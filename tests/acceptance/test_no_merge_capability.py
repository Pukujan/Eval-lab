"""The application must not be able to merge, push, or deploy (T-6).

Enforced by absence: there is no VCS-write client anywhere in `app/`. This test
scans for one so the property survives future edits.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

APPLICATION_ROOTS = ("app", "evals")

FORBIDDEN_CALL_PATTERNS = (
    re.compile(r"""git\s+push""", re.IGNORECASE),
    re.compile(r"""git\s+merge""", re.IGNORECASE),
    re.compile(r"""git\s+commit""", re.IGNORECASE),
    re.compile(r"""merge_pull_request""", re.IGNORECASE),
    re.compile(r"""create_pull_request""", re.IGNORECASE),
    re.compile(r"""\bkubectl\b""", re.IGNORECASE),
    re.compile(r"""\bterraform\s+apply\b""", re.IGNORECASE),
    re.compile(r"""\bdocker\s+push\b""", re.IGNORECASE),
)

FORBIDDEN_IMPORTS = ("github", "pygithub", "gitlab", "git", "dulwich")


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in APPLICATION_ROOTS:
        files.extend(path for path in Path(root).rglob("*.py") if "__pycache__" not in path.parts)
    return files


@pytest.mark.parametrize("path", _python_files(), ids=str)
def test_no_vcs_write_or_deploy_calls(path: Path) -> None:
    source = path.read_text(encoding="utf-8")
    for pattern in FORBIDDEN_CALL_PATTERNS:
        assert not pattern.search(source), (
            f"{path} references a merge/push/deploy operation: {pattern.pattern}"
        )


@pytest.mark.parametrize("path", _python_files(), ids=str)
def test_no_vcs_client_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)

    offenders = [name for name in imported if name.split(".")[0].lower() in FORBIDDEN_IMPORTS]
    assert not offenders, f"{path} imports a VCS client: {offenders}"


def test_the_only_positive_outcome_is_a_recommendation() -> None:
    from app.reliability.report import OUTCOME_MEANING

    assert "merged or deployed" in OUTCOME_MEANING["accepted_for_review"]


def test_git_is_only_used_read_only() -> None:
    """`runner.py` reads a revision for the manifest; that is the only git use."""
    source = Path("app/runner.py").read_text(encoding="utf-8")
    assert "rev-parse" in source
    for verb in ("push", "commit", "merge", "checkout", "reset"):
        assert f'"{verb}"' not in source, f"runner.py invokes git {verb}"
