"""Validate the machine-readable TASK-0010 research artifact bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import yaml
from pyshacl import validate
from rdflib import Graph


def _check_checksums(root: Path) -> None:
    checksum_path = root / "checksums.sha256"
    for line in checksum_path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        actual = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual != digest:
            raise ValueError(f"checksum mismatch for {name}")


def validate_bundle(benchmark: Path) -> dict[str, object]:
    _check_checksums(benchmark)
    crate = json.loads((benchmark / "ro-crate-metadata.json").read_text(encoding="utf-8"))
    if crate.get("@context") != "https://w3id.org/ro/crate/1.3/context":
        raise ValueError("RO-Crate context is not 1.3")
    Graph().parse(benchmark / "provenance.ttl", format="turtle")
    shapes = Graph().parse(benchmark / "shapes.ttl", format="turtle")
    data = Graph().parse(benchmark / "provenance.ttl", format="turtle")
    conforms, _, report_text = validate(data_graph=data, shacl_graph=shapes, inference="rdfs")
    if not conforms:
        raise ValueError(f"SHACL validation failed: {report_text}")
    citation = yaml.safe_load(Path("CITATION.cff").read_text(encoding="utf-8"))
    required_citation = {"cff-version", "title", "authors", "repository-code", "version"}
    if not required_citation <= set(citation):
        raise ValueError("CITATION.cff is missing required keys")
    for path in (Path("paper/main.tex"), Path("paper/reproducibility.md"), Path("paper/limitations.md")):
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            raise ValueError(f"missing paper artifact: {path}")
    return {
        "checksums": "ok",
        "ro_crate": "ok",
        "prov_o": "parsed",
        "shacl": "conforms",
        "citation": "parsed",
        "paper": "present",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, default=Path("benchmark/eval-lab-select-v0.1.0"))
    args = parser.parse_args()
    print(json.dumps(validate_bundle(args.benchmark), sort_keys=True))


if __name__ == "__main__":
    main()
