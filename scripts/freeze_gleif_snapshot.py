"""Freeze the GLEIF Golden Copy snapshot for EXP-026.

Download the two dated GLEIF Golden Copy archives named in the EXP-026 source
manifest, verify each archive byte-for-byte against the recorded SHA-256 and
size, extract the CSV payload, and record the literal header row and observed
data-row count. The raw archives are a local cache and are never committed; the
committed ``frozen-snapshot.json`` records only hashes, the observed header, and
counts, so the canonical build is reproducible from a re-download.

Raw archives live outside the dev root, under the ACS cache by default
(``%LOCALAPPDATA%\\acs\\scratch\\gleif-snapshot`` on Windows,
``~/.cache/acs/scratch/gleif-snapshot`` elsewhere); ``GLEIF_CACHE_DIR`` or
``--cache-dir`` overrides it.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments" / "EXP-20260922-026-gleif-objective-track"
MANIFEST_PATH = EXPERIMENT_DIR / "source-manifest.json"
FROZEN_PATH = EXPERIMENT_DIR / "frozen-snapshot.json"
USER_AGENT = "eval-lab-gleif-freeze/1.0 (+https://github.com/Pukujan/Eval-lab)"
_CHUNK = 1 << 20


def default_cache_dir() -> Path:
    override = os.environ.get("GLEIF_CACHE_DIR")
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "acs" / "scratch" / "gleif-snapshot"
    return Path.home() / ".cache" / "acs" / "scratch" / "gleif-snapshot"


def sha256_and_size(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(_CHUNK):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def download(url: str, destination: Path, *, expected_bytes: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    written = 0
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request) as response, partial.open("wb") as sink:
        while chunk := response.read(_CHUNK):
            sink.write(chunk)
            digest.update(chunk)
            written += len(chunk)
    if written != expected_bytes:
        partial.unlink(missing_ok=True)
        raise ValueError(f"downloaded {written} bytes, manifest records {expected_bytes}: {url}")
    partial.replace(destination)


def ensure_archive(entry: dict, cache_dir: Path) -> Path:
    destination = cache_dir / entry["name"]
    if destination.is_file():
        digest, size = sha256_and_size(destination)
        if digest == entry["sha256"] and size == entry["bytes"]:
            return destination
    download(entry["url"], destination, expected_bytes=entry["bytes"])
    digest, size = sha256_and_size(destination)
    if digest != entry["sha256"]:
        raise ValueError(f"archive hash mismatch for {entry['name']}: {digest}")
    if size != entry["bytes"]:
        raise ValueError(f"archive size mismatch for {entry['name']}: {size}")
    return destination


def extract_csv(archive: Path, cache_dir: Path) -> Path:
    with zipfile.ZipFile(archive) as bundle:
        members = [name for name in bundle.namelist() if name.lower().endswith(".csv")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV in {archive.name}, found {members}")
        member = members[0]
        target = cache_dir / Path(member).name
        if not target.is_file() or target.stat().st_size == 0:
            bundle.extract(member, cache_dir)
            extracted = cache_dir / member
            if extracted != target:
                extracted.replace(target)
    return target


def header_and_count(csv_path: Path) -> tuple[list[str], int]:
    rows = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(f"empty CSV: {csv_path.name}") from exc
        for _ in reader:
            rows += 1
    return header, rows


def freeze(cache_dir: Path) -> dict:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    frozen_files = []
    for entry in manifest["files"]:
        archive = ensure_archive(entry, cache_dir)
        csv_path = extract_csv(archive, cache_dir)
        header, rows = header_and_count(csv_path)
        frozen_files.append(
            {
                "name": entry["name"],
                "csv_name": csv_path.name,
                "bytes": entry["bytes"],
                "sha256": entry["sha256"],
                "cdf_version": entry.get("cdf_version"),
                "column_count": len(header),
                "header": header,
                "data_row_count": rows,
            }
        )
    frozen = {
        "source": manifest["source"],
        "snapshot_date": manifest["snapshot_date"],
        "license": manifest["license"],
        "frozen_at_utc": datetime.now(UTC).isoformat(),
        "files": frozen_files,
    }
    FROZEN_PATH.write_text(json.dumps(frozen, indent=2) + "\n", encoding="utf-8")
    return frozen


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir())
    args = parser.parse_args()
    try:
        frozen = freeze(args.cache_dir)
    except (OSError, ValueError) as exc:
        print(f"GLEIF freeze stopped: {exc}", file=sys.stderr)
        return 1
    for entry in frozen["files"]:
        print(
            f"{entry['name']}: {entry['data_row_count']} rows, "
            f"{entry['column_count']} columns -> {entry['csv_name']}"
        )
    print(f"wrote {FROZEN_PATH.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
