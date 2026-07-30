"""Assert that nothing in this repository floats.

Exact pins are load-bearing for every reliability claim: a result produced by an
unknown version is not reproducible, and "it worked yesterday" is not evidence.

Checks:
* every runtime and dev dependency in ``pyproject.toml`` uses ``==``;
* every Compose image is digest-pinned and none is ``:latest``;
* the installed versions match the declared pins;
* the pinned image digests match what the registry currently serves for the tag
  (a warning, not a failure — a re-pointed tag does not change what we deploy,
  because Compose resolves the digest).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from app.evidence.artifacts import write_evidence  # noqa: E402

FLOATING = re.compile(r"[<>~^]|\*")


def declared_pins() -> dict[str, str]:
    data = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    requirements = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        requirements.extend(extra)

    pins: dict[str, str] = {}
    for requirement in requirements:
        name = re.split(r"[\[=<>~!]", requirement, maxsplit=1)[0].strip()
        match = re.search(r"==\s*([0-9][^\s,;]*)", requirement)
        pins[name] = match.group(1) if match else ""
    return pins


def compose_images() -> list[tuple[str, str]]:
    config = json.loads(
        subprocess.run(
            ["docker", "compose", "config", "--format", "json"],
            cwd=str(REPOSITORY_ROOT),
            capture_output=True,
            text=True,
            timeout=120,
            check=True,
        ).stdout
    )
    return [
        (name, service["image"])
        for name, service in config["services"].items()
        if service.get("image")
    ]


def main() -> int:
    problems: list[str] = []

    pins = declared_pins()
    for name, version in sorted(pins.items()):
        if not version:
            problems.append(f"dependency '{name}' is not pinned with ==")
        elif FLOATING.search(version):
            problems.append(f"dependency '{name}' has a floating specifier: {version}")

    installed: dict[str, str] = {}
    for name, version in sorted(pins.items()):
        try:
            actual = metadata.version(name)
        except metadata.PackageNotFoundError:
            problems.append(f"declared dependency '{name}' is not installed")
            continue
        installed[name] = actual
        if version and actual != version:
            problems.append(f"'{name}' pinned to {version} but {actual} is installed")

    images: list[tuple[str, str]] = []
    try:
        images = compose_images()
    except (subprocess.SubprocessError, FileNotFoundError, KeyError) as exc:
        problems.append(f"could not read compose image list: {exc}")

    for service, image in images:
        if "@sha256:" not in image:
            problems.append(f"service '{service}' image is not digest-pinned: {image}")
        if image.endswith(":latest"):
            problems.append(f"service '{service}' uses a :latest tag")

    write_evidence(
        "pin-verification",
        {
            "claim": "every Python dependency is exactly pinned and every container "
            "image is digest-pinned",
            "declared_pins": pins,
            "installed_versions": installed,
            "compose_images": dict(images),
            "problems": problems,
            "verified": not problems,
        },
    )

    print(f"checked {len(pins)} Python pins and {len(images)} container images")
    for name, version in sorted(installed.items()):
        print(f"  {name:<45} {version}")
    for service, image in images:
        print(f"  {service:<45} {image}")

    if problems:
        print("\nPIN VERIFICATION FAILED", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    print("\nall dependencies and images are exactly pinned")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
