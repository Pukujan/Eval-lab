"""TASK-0071: the dynamic-update claim, demonstrated end to end in a browser.

Acceptance criterion 4 says the viewer "reflects a new eval run without a page
reload, demonstrated by an automated browser test". This module is that
demonstration: it starts the real server, drives a real Chromium, mutates a
served artifact mid-session, and asserts the UI changed with no navigation.

The browser driver is the one vendored in the `app-builder-automation`
workspace, which is not a dependency of this repository, so the test **skips**
where it is absent (as it is in CI) rather than failing. The deterministic
proof of the same mechanism that CI does run lives in `tests/test_viewer_api.py`
(`test_revision_endpoint_reports_a_change_after_a_served_byte_moves`).

Run it locally with::

    uv run --locked python -m pytest tests/test_viewer_polling_e2e.py -q
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from eval_lab.viewer_api import INPUT_FILES, ITEMS_DOC, REVISION_FILES
from scripts.serve_classifier_viewer import build_server

ROOT = Path(__file__).resolve().parents[1]
# The sibling checkout under the parent directory (AGENTS.md: D:\development
# holds only the main checkout of each repository), overridable for other hosts.
AUTOMATION_ROOT = Path(
    os.environ.get("EVAL_LAB_AUTOMATION_ROOT", ROOT.parent / "app-builder-automation")
)
DRIVER = AUTOMATION_ROOT / "eval/out/poll-viewer.mjs"
PLAYWRIGHT = AUTOMATION_ROOT / "node_modules/playwright"


def _require_driver() -> None:
    if not DRIVER.is_file() or not PLAYWRIGHT.is_dir():
        pytest.skip(f"browser driver not installed at {DRIVER}")


def _mirror(destination: Path) -> Path:
    """A served root whose artifacts the test may mutate without touching git.

    The whole static bundle plus every file the server reads is copied, because
    the revision memo key stats the upstream inputs as well as the served ones.
    """
    shutil.copytree(ROOT / "site/gleif-classifier", destination / "site/gleif-classifier")
    for relative in sorted(set(REVISION_FILES) | set(INPUT_FILES)):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return destination


@pytest.fixture(scope="module")
def served(tmp_path_factory: pytest.TempPathFactory) -> Iterator[tuple[str, Path]]:
    root = _mirror(tmp_path_factory.mktemp("viewer-root"))
    server = build_server(root=root, host="127.0.0.1", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}", root
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def test_viewer_updates_without_a_reload_when_a_served_artifact_changes(
    served: tuple[str, Path],
) -> None:
    _require_driver()
    origin, root = served
    items = root / ITEMS_DOC
    original = items.read_bytes()
    try:
        completed = subprocess.run(
            [
                "node",
                str(DRIVER),
                "--url",
                origin,
                "--items",
                str(items),
                "--poll-ms",
                "1000",
            ],
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    finally:
        items.write_bytes(original)

    assert completed.returncode == 0, f"driver failed:\n{completed.stdout}\n{completed.stderr}"
    verdict = json.loads(completed.stdout)
    assert verdict["failures"] == [], verdict["failures"]
    assert verdict["consoleErrors"] == [] and verdict["pageErrors"] == []
    assert verdict["beforeRevision"] != verdict["afterRevision"]
    assert verdict["afterScored"] == "100"


def test_the_server_was_reachable_for_the_whole_run(served: tuple[str, Path]) -> None:
    """Cheap companion assertion, so a driver skip still checks the fixture."""
    origin, _ = served
    with httpx.Client(base_url=origin, timeout=10) as client:
        payload = client.get("/api/v1/revision").json()
        assert payload["recordCount"] == 2142
        assert client.get("/api/v1/revision").headers["Cache-Control"] == "no-store"
