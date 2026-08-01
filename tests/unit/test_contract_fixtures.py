"""The frozen Milestone 2 contracts, checked against their own fixtures.

Offline. No network, no gateway, no verifier repository, no GitHub API.

**Why this file carries its own validator.** `jsonschema` is present in this
environment only as a transitive dependency of the model gateway, and the
milestone brief forbids adding a dependency to satisfy a test. So the checker
below is the source of truth, and it implements *only the subset of JSON Schema
draft 2020-12 that the four contract schemas actually use*: `$ref` (local and by
`$id`), `$defs`, `oneOf`, `type`, `const`, `enum`, `required`, `properties`,
`additionalProperties: false`, `items`, `minItems`, `maxItems`, `uniqueItems`,
`pattern`, `minLength`, `maxLength`, `minimum`, `maximum`. It does not implement
`if`/`then`, `dependentSchemas`, `patternProperties`, `format`, `contains`,
`prefixItems`, numeric `multipleOf`, or annotation collection, and it is not a
conformant implementation of the specification. A test asserts that the schemas
use no keyword outside that list, so the gap cannot widen silently. Where the
real library *is* importable, every accept/reject verdict below is additionally
cross-checked against it, and a disagreement fails.

**Why rejection alone is not the assertion.** A validator that rejects
everything would pass a test that only asserts hostile fixtures fail. Each
hostile fixture's manifest entry therefore names the exact violation — a stable
code plus a JSON Pointer — and the test asserts that the checker produces that
violation and no other. Getting the right answer for the wrong reason is the
failure mode these fixtures exist to catch.

**Why there is a checker and not just a validator.** Four of the hostile
properties are invisible to schema validation by construction: a digest that
does not match the bytes it names, a document edited after it was sealed, an
archive entry nobody declared, and an attestation bound to a different bundle.
Those are decided by recomputing digests and comparing declarations against the
declarative materialisation recorded in the fixture manifest. The checker here is
a *reference* implementation for the intake and verifier-boundary workstreams to
target, not the shipped one.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
SCHEMA_DIR = CONTRACTS / "schemas"
FIXTURE_DIR = CONTRACTS / "fixtures"
MANIFEST_PATH = FIXTURE_DIR / "manifest.json"

INTAKE_ID = "https://contracts.eval-lab.invalid/evidence-intake/1.0.0.schema.json"
OUTCOME_ID = "https://contracts.eval-lab.invalid/evallab-outcome/1.0.0.schema.json"
ENVELOPE_ID = "https://contracts.eval-lab.invalid/verifier-envelope/1.0.0.schema.json"
JOBSPEC_ID = "https://contracts.eval-lab.invalid/jobspec-reference/1.0.0.schema.json"

PERMITTED_OUTCOMES = (
    "accepted_for_review",
    "rejected",
    "abstained",
    "infrastructure_failure",
)
FORBIDDEN_OUTCOMES = ("approved", "correct", "safe", "production_ready")

#: Every keyword the built-in checker implements. A schema that uses anything
#: else would be silently under-validated, so the set is asserted, not assumed.
SUPPORTED_KEYWORDS = frozenset(
    {
        "$schema",
        "$id",
        "$ref",
        "$defs",
        "title",
        "description",
        "type",
        "const",
        "enum",
        "required",
        "properties",
        "additionalProperties",
        "items",
        "minItems",
        "maxItems",
        "uniqueItems",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "oneOf",
    }
)


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _schema_files() -> list[Path]:
    return sorted(SCHEMA_DIR.glob("*.schema.json"))


REGISTRY: dict[str, dict[str, Any]] = {
    str(_load_json(path)["$id"]): _load_json(path) for path in _schema_files()
}
MANIFEST: dict[str, Any] = _load_json(MANIFEST_PATH)
FIXTURES: list[dict[str, Any]] = MANIFEST["fixtures"]


def _fixture(fixture_id: str) -> dict[str, Any]:
    for entry in FIXTURES:
        if entry["fixture_id"] == fixture_id:
            return entry
    raise AssertionError(f"no manifest entry for {fixture_id}")


def _document(entry: dict[str, Any]) -> Any:
    return _load_json(FIXTURE_DIR / entry["file"])


def _schema_for(entry: dict[str, Any]) -> dict[str, Any]:
    return _load_json(CONTRACTS / entry["schema"])


# ---------------------------------------------------------------------------
# The structural validator (documented subset only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Violation:
    """One refusal, named precisely enough to be a target.

    ``pointer`` is an RFC 6901 JSON Pointer at the *instance* location that
    failed, so "rejected" and "rejected for the right reason" are different
    assertions.
    """

    code: str
    pointer: str
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "pointer": self.pointer, "detail": self.detail}


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _json_equal(left: Any, right: Any) -> bool:
    """Strict JSON equality. Python's ``True == 1`` would make ``const: true``
    accept the integer 1, which is exactly the kind of loose acceptance these
    schemas exist to prevent."""
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_json_equal(left[k], right[k]) for k in left)
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            _json_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return type(left) is type(right) and left == right


def _type_matches(instance: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(instance, dict)
    if expected == "array":
        return isinstance(instance, list)
    if expected == "string":
        return isinstance(instance, str)
    if expected == "boolean":
        return isinstance(instance, bool)
    if expected == "integer":
        return isinstance(instance, int) and not isinstance(instance, bool)
    if expected == "number":
        return isinstance(instance, int | float) and not isinstance(instance, bool)
    if expected == "null":
        return instance is None
    raise AssertionError(f"unsupported type keyword {expected!r}")


def _resolve(ref: str, root: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return (subschema, the root it must be resolved against)."""
    if ref.startswith("#/"):
        node: Any = root
        for token in ref[2:].split("/"):
            node = node[token.replace("~1", "/").replace("~0", "~")]
        return node, root
    target = REGISTRY[ref]
    return target, target


def _validate(
    instance: Any,
    schema: dict[str, Any],
    pointer: str,
    root: dict[str, Any],
    out: list[Violation],
) -> None:
    if "$ref" in schema:
        target, target_root = _resolve(schema["$ref"], root)
        _validate(instance, target, pointer, target_root, out)

    if "oneOf" in schema:
        _validate_one_of(instance, schema["oneOf"], pointer, root, out)

    if "type" in schema and not _type_matches(instance, schema["type"]):
        out.append(Violation("type_mismatch", pointer, schema["type"]))
        return

    if "const" in schema and not _json_equal(instance, schema["const"]):
        code = "const_mismatch"
        if pointer.endswith(("/schema_version", "/envelope_version")):
            code = "unsupported_schema_version"
        # ``detail`` names the value that WAS supported, so a rejection tells a
        # producer which version to build against rather than only that it lost.
        expected = schema["const"]
        out.append(Violation(code, pointer, expected if isinstance(expected, str) else None))

    if "enum" in schema and not any(_json_equal(instance, option) for option in schema["enum"]):
        out.append(Violation("enum_not_allowed", pointer))

    if isinstance(instance, str):
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            out.append(Violation("pattern_mismatch", pointer))
        if "minLength" in schema and len(instance) < schema["minLength"]:
            out.append(Violation("string_length_out_of_range", pointer))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            out.append(Violation("string_length_out_of_range", pointer))

    if isinstance(instance, int | float) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            out.append(Violation("value_out_of_range", pointer))
        if "maximum" in schema and instance > schema["maximum"]:
            out.append(Violation("value_out_of_range", pointer))

    if isinstance(instance, dict):
        _validate_object(instance, schema, pointer, root, out)

    if isinstance(instance, list):
        _validate_array(instance, schema, pointer, root, out)


def _validate_object(
    instance: dict[str, Any],
    schema: dict[str, Any],
    pointer: str,
    root: dict[str, Any],
    out: list[Violation],
) -> None:
    for name in schema.get("required", []):
        if name not in instance:
            out.append(Violation("required_property_missing", pointer, name))

    properties = schema.get("properties", {})
    if schema.get("additionalProperties") is False and properties:
        for name in instance:
            if name not in properties:
                out.append(Violation("unexpected_property", pointer, name))

    for name, subschema in properties.items():
        if name in instance:
            _validate(instance[name], subschema, f"{pointer}/{_escape(name)}", root, out)


def _validate_array(
    instance: list[Any],
    schema: dict[str, Any],
    pointer: str,
    root: dict[str, Any],
    out: list[Violation],
) -> None:
    if "minItems" in schema and len(instance) < schema["minItems"]:
        out.append(Violation("array_length_out_of_range", pointer))
    if "maxItems" in schema and len(instance) > schema["maxItems"]:
        out.append(Violation("array_length_out_of_range", pointer))
    if schema.get("uniqueItems"):
        seen = [json.dumps(item, sort_keys=True) for item in instance]
        if len(set(seen)) != len(seen):
            out.append(Violation("array_items_not_unique", pointer))
    if "items" in schema:
        for index, item in enumerate(instance):
            _validate(item, schema["items"], f"{pointer}/{index}", root, out)


def _validate_one_of(
    instance: Any,
    branches: list[dict[str, Any]],
    pointer: str,
    root: dict[str, Any],
    out: list[Violation],
) -> None:
    """Report the failure of the branch the document was *trying* to be.

    Reporting every branch's failures would bury the real one. The contract
    schemas discriminate with a ``const`` member (``record_type``), so the
    intended branch is knowable; where it is not, the closest branch is used.
    """
    attempts: list[list[Violation]] = []
    for branch in branches:
        collected: list[Violation] = []
        _validate(instance, branch, pointer, root, collected)
        attempts.append(collected)

    matching = [i for i, found in enumerate(attempts) if not found]
    if len(matching) == 1:
        return
    if len(matching) > 1:
        out.append(Violation("one_of_ambiguous", pointer))
        return

    intended = min(range(len(attempts)), key=lambda i: len(attempts[i]))
    if isinstance(instance, dict) and "record_type" in instance:
        for index, branch in enumerate(branches):
            resolved, _ = _resolve(branch["$ref"], root) if "$ref" in branch else (branch, root)
            declared = resolved.get("properties", {}).get("record_type", {}).get("const")
            if declared == instance["record_type"]:
                intended = index
                break
    out.extend(attempts[intended])


def validate(instance: Any, schema: dict[str, Any]) -> list[Violation]:
    """Structural validation only. See the module docstring for the covered subset."""
    found: list[Violation] = []
    _validate(instance, schema, "", schema, found)
    return found


# ---------------------------------------------------------------------------
# Digest and materialisation checks (what schema validation cannot see)
# ---------------------------------------------------------------------------


def canonical(payload: Any) -> bytes:
    """The exact bytes a manifest digest covers.

    Sorted keys, no insignificant whitespace, non-ASCII escaped, UTF-8 — the
    same convention as ``app.domain.schemas._Base.content_hash``. It is written
    down in the schema description and in the fixture manifest because two
    encoders that disagree here would make the digest a property of the encoder
    rather than of the document.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def recompute_manifest_digest(document: dict[str, Any]) -> str:
    stripped = {k: v for k, v in document.items() if k != "manifest_digest"}
    return hashlib.sha256(canonical(stripped)).hexdigest()


def check_bundle(document: Any, materialisation: dict[str, Any]) -> list[Violation]:
    """The reference intake check: schema first, then everything schema cannot see.

    Schema violations short-circuit deliberately. A document that is structurally
    wrong cannot be meaningfully digest-checked, and reporting both would make
    the primary reason ambiguous.
    """
    schema_violations = validate(document, REGISTRY[INTAKE_ID])
    if schema_violations:
        return schema_violations

    found: list[Violation] = []
    if document["manifest_digest"] != recompute_manifest_digest(document):
        found.append(Violation("manifest_digest_mismatch", "/manifest_digest"))

    jobspec_bytes = materialisation.get("jobspec_bytes")
    if jobspec_bytes is not None:
        declared = document["jobspec_reference"]["jobspec_digest"]
        if declared != sha256_text(jobspec_bytes):
            found.append(Violation("jobspec_digest_mismatch", "/jobspec_reference/jobspec_digest"))

    entries = {entry["name"]: entry for entry in materialisation.get("entries", [])}
    artifacts = document["candidate_artifacts"]

    for index, artifact in enumerate(artifacts):
        entry = entries.get(artifact["path"])
        if entry is None:
            found.append(
                Violation("declared_artifact_absent", f"/candidate_artifacts/{index}/path")
            )
            continue
        if entry["entry_type"] != "file":
            found.append(
                Violation(
                    "symlink_archive_entry_refused",
                    f"/candidate_artifacts/{index}/path",
                    entry.get("link_target"),
                )
            )
            continue
        content = entry.get("content")
        computed = sha256_text(content) if content is not None else entry["sha256"]
        if artifact["sha256"] != computed:
            found.append(
                Violation("artifact_digest_mismatch", f"/candidate_artifacts/{index}/sha256")
            )
        elif content is not None and artifact["size_bytes"] != len(content.encode("utf-8")):
            found.append(
                Violation("artifact_size_mismatch", f"/candidate_artifacts/{index}/size_bytes")
            )

    declared_paths = {artifact["path"] for artifact in artifacts}
    for name in entries:
        if name not in declared_paths:
            found.append(Violation("undeclared_archive_entry", "/candidate_artifacts", name))

    found.extend(_check_attempt_lineage(document))
    found.extend(_check_visible_tests(document))
    return found


def _check_attempt_lineage(document: dict[str, Any]) -> list[Violation]:
    """Ordering and retry consistency, which JSON Schema cannot state."""
    found: list[Violation] = []
    attempts = document["attempts"]
    for index, attempt in enumerate(attempts):
        if attempt["attempt_index"] != index:
            found.append(
                Violation("attempt_lineage_disordered", f"/attempts/{index}/attempt_index")
            )
    if attempts and attempts[0]["is_retry"]:
        found.append(Violation("attempt_retry_flag_inconsistent", "/attempts/0/is_retry"))
    budget = document["jobspec_reference"]["retry_budget"]
    if len(attempts) > max(budget, 1):
        found.append(Violation("attempt_budget_exceeded", "/attempts"))
    return found


def _check_visible_tests(document: dict[str, Any]) -> list[Violation]:
    """Each summary must reconcile with itself and name a declared report."""
    found: list[Violation] = []
    digests = {artifact["sha256"] for artifact in document["candidate_artifacts"]}
    for phase, result in document["visible_test_results"].items():
        counted = result["passed"] + result["failed"] + result["errors"] + result["skipped"]
        if counted != result["total"]:
            found.append(
                Violation("test_counts_inconsistent", f"/visible_test_results/{phase}/total")
            )
        if result["report_sha256"] not in digests:
            found.append(
                Violation(
                    "test_report_not_declared",
                    f"/visible_test_results/{phase}/report_sha256",
                )
            )
    return found


def check_outcome(document: Any, materialisation: dict[str, Any]) -> list[Violation]:
    """The reference outcome check: schema, gate ordering, attestation binding."""
    schema_violations = validate(document, REGISTRY[OUTCOME_ID])
    if schema_violations:
        return schema_violations

    found: list[Violation] = []
    for index, gate in enumerate(document["gate_results"]):
        if gate["order"] != index:
            found.append(Violation("gate_order_disordered", f"/gate_results/{index}/order"))

    attestation = document["verifier_attestation"]
    if attestation is None:
        return found

    bundle_id = materialisation.get("bundle_fixture")
    bundle = _document(_fixture(bundle_id)) if bundle_id else None

    if bundle is not None and document["bundle_manifest_digest"] != bundle["manifest_digest"]:
        found.append(Violation("bundle_binding_mismatch", "/bundle_manifest_digest"))
    if attestation["bound_manifest_digest"] != document["bundle_manifest_digest"]:
        found.append(
            Violation(
                "attestation_binding_mismatch",
                "/verifier_attestation/bound_manifest_digest",
            )
        )
    if bundle is not None:
        expected_jobspec = bundle["jobspec_reference"]["jobspec_digest"]
        if attestation["bound_jobspec_digest"] != expected_jobspec:
            found.append(
                Violation(
                    "attestation_binding_mismatch",
                    "/verifier_attestation/bound_jobspec_digest",
                )
            )
        expected_artifacts = {a["sha256"] for a in bundle["candidate_artifacts"]}
        if set(attestation["bound_artifact_digests"]) != expected_artifacts:
            found.append(
                Violation(
                    "attestation_binding_mismatch",
                    "/verifier_attestation/bound_artifact_digests",
                )
            )
    return found


def check_fixture(entry: dict[str, Any]) -> list[Violation]:
    document = _document(entry)
    materialisation = entry.get("materialisation") or {}
    if entry["schema"].endswith("evallab-outcome-1.0.0.schema.json"):
        return check_outcome(document, materialisation)
    return check_bundle(document, materialisation)


# ---------------------------------------------------------------------------
# Optional cross-check against the real library
# ---------------------------------------------------------------------------


def _jsonschema_validator(schema: dict[str, Any]) -> Any | None:
    """Return a real draft 2020-12 validator, or None when unavailable.

    ``jsonschema`` is not a declared dependency of this project, so its absence
    is normal and must not fail or skip anything. Its presence is used only to
    corroborate verdicts the built-in checker already produced.
    """
    try:
        from jsonschema import Draft202012Validator
        from referencing import Registry, Resource
    except ImportError:  # pragma: no cover - depends on the environment
        return None

    registry = Registry().with_resources(
        (identifier, Resource.from_contents(contents)) for identifier, contents in REGISTRY.items()
    )
    return Draft202012Validator(schema, registry=registry)


HAVE_JSONSCHEMA = _jsonschema_validator(REGISTRY[INTAKE_ID]) is not None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_schema_is_valid_json_and_self_describing(path: Path) -> None:
    schema = _load_json(path)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].startswith("https://contracts.eval-lab.invalid/")
    assert schema["title"]
    assert len(schema["description"]) > 200, "a schema must say what it deliberately omits"


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_schema_compiles_under_the_real_library(path: Path) -> None:
    if not HAVE_JSONSCHEMA:  # pragma: no cover - depends on the environment
        pytest.skip("jsonschema is not installed; the built-in checker is authoritative")
    from jsonschema import Draft202012Validator

    Draft202012Validator.check_schema(_load_json(path))


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_schema_uses_only_keywords_the_builtin_checker_implements(path: Path) -> None:
    """The built-in checker covers a subset; the schemas must stay inside it."""
    used: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"properties", "$defs"}:
                    for child in value.values():
                        walk(child)
                    used.add(key)
                    continue
                used.add(key)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(_load_json(path))
    assert used <= SUPPORTED_KEYWORDS, (
        f"unimplemented keywords: {sorted(used - SUPPORTED_KEYWORDS)}"
    )


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_every_object_level_forbids_additional_properties(path: Path) -> None:
    """An unexpected extra member must be detectable anywhere, not just at the root."""
    offenders: list[str] = []

    def walk(node: Any, where: str) -> None:
        if isinstance(node, dict):
            if "properties" in node and node.get("additionalProperties") is not False:
                offenders.append(where)
            for key, value in node.items():
                walk(value, f"{where}/{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{where}/{index}")

    walk(_load_json(path), path.name)
    assert offenders == []


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_every_digest_field_requires_lowercase_hex_sha256(path: Path) -> None:
    offenders: list[str] = []

    def walk(node: Any, where: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "properties":
                    for name, subschema in value.items():
                        if name.endswith(("_digest", "sha256")) and isinstance(subschema, dict):
                            if subschema.get("pattern") != "^[a-f0-9]{64}$":
                                offenders.append(f"{where}/{name}")
                        walk(subschema, f"{where}/{name}")
                else:
                    walk(value, f"{where}/{key}")
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{where}/{index}")

    walk(_load_json(path), path.name)
    assert offenders == []


def _walk_refs(node: Any, root: dict[str, Any]) -> None:
    if isinstance(node, dict):
        if "$ref" in node:
            _resolve(node["$ref"], root)
        for value in node.values():
            _walk_refs(value, root)
    elif isinstance(node, list):
        for item in node:
            _walk_refs(item, root)


def test_every_reference_resolves() -> None:
    """A dangling $ref would make a schema look stricter than it is."""
    for schema in REGISTRY.values():
        _walk_refs(schema, schema)


# ---------------------------------------------------------------------------
# Manifest and fixture correspondence
# ---------------------------------------------------------------------------


def test_manifest_and_fixture_files_are_in_bijection() -> None:
    on_disk = {
        str(path.relative_to(FIXTURE_DIR))
        for path in FIXTURE_DIR.rglob("*.json")
        if path != MANIFEST_PATH
    }
    in_manifest = {entry["file"] for entry in FIXTURES}
    assert in_manifest == on_disk


def test_manifest_holds_exactly_the_frozen_sixteen() -> None:
    assert len(FIXTURES) == 16
    assert sum(1 for entry in FIXTURES if entry["category"] == "valid") == 3
    assert sum(1 for entry in FIXTURES if entry["category"] == "hostile") == 13
    assert len({entry["fixture_id"] for entry in FIXTURES}) == 16


@pytest.mark.parametrize("entry", FIXTURES, ids=lambda e: e["fixture_id"])
def test_every_manifest_entry_is_complete(entry: dict[str, Any]) -> None:
    assert entry["property_exercised"]
    assert (CONTRACTS / entry["schema"]).exists()
    if entry["category"] == "hostile":
        assert entry["expected_rejection"]["code"]
        assert len(entry["expected_rejection_reason"]) > 40
    else:
        assert entry["expected_rejection"] is None


@pytest.mark.parametrize("entry", FIXTURES, ids=lambda e: e["fixture_id"])
def test_materialisation_entries_are_self_consistent(entry: dict[str, Any]) -> None:
    """Where the manifest states bytes, its own recorded digest must match them.

    Otherwise a digest-mismatch test could pass because the *manifest* was wrong.
    """
    for archive_entry in (entry.get("materialisation") or {}).get("entries", []):
        content = archive_entry.get("content")
        if content is None:
            continue
        assert archive_entry["sha256"] == sha256_text(content)
        assert archive_entry["size_bytes"] == len(content.encode("utf-8"))


# ---------------------------------------------------------------------------
# Valid fixtures
# ---------------------------------------------------------------------------

VALID_FIXTURES = [entry for entry in FIXTURES if entry["category"] == "valid"]
HOSTILE_FIXTURES = [entry for entry in FIXTURES if entry["category"] == "hostile"]


@pytest.mark.parametrize("entry", VALID_FIXTURES, ids=lambda e: e["fixture_id"])
def test_valid_fixture_passes_schema_validation(entry: dict[str, Any]) -> None:
    assert validate(_document(entry), _schema_for(entry)) == []


@pytest.mark.parametrize("entry", VALID_FIXTURES, ids=lambda e: e["fixture_id"])
def test_valid_fixture_passes_the_full_reference_check(entry: dict[str, Any]) -> None:
    assert check_fixture(entry) == []


@pytest.mark.parametrize("entry", VALID_FIXTURES, ids=lambda e: e["fixture_id"])
def test_valid_fixture_agrees_with_the_real_library(entry: dict[str, Any]) -> None:
    if not HAVE_JSONSCHEMA:  # pragma: no cover - depends on the environment
        pytest.skip("jsonschema is not installed; the built-in checker is authoritative")
    validator = _jsonschema_validator(_schema_for(entry))
    assert validator is not None
    assert list(validator.iter_errors(_document(entry))) == []


def test_failed_attempts_bundle_is_evidence_not_malformed_input() -> None:
    """A job that did not succeed still produced a record of not succeeding."""
    entry = _fixture("valid_failed_attempts")
    document = _document(entry)
    assert check_fixture(entry) == []
    assert [attempt["outcome"] for attempt in document["attempts"]] == ["failed", "failed"]
    assert document["visible_test_results"]["final"]["failed"] > 0


def test_bounded_retry_lineage_stays_within_the_declared_budget() -> None:
    document = _document(_fixture("valid_bounded_retry"))
    attempts = document["attempts"]
    assert [a["is_retry"] for a in attempts] == [False, True, True]
    assert len(attempts) <= document["jobspec_reference"]["retry_budget"]


# ---------------------------------------------------------------------------
# Hostile fixtures — rejected, and for the named reason
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", HOSTILE_FIXTURES, ids=lambda e: e["fixture_id"])
def test_hostile_fixture_is_rejected_for_exactly_the_named_reason(entry: dict[str, Any]) -> None:
    expected = entry["expected_rejection"]
    found = [violation.as_dict() for violation in check_fixture(entry)]
    assert found == [expected], (
        f"{entry['fixture_id']}: expected exactly {expected}, got {found}. "
        f"Manifest reason: {entry['expected_rejection_reason']}"
    )


@pytest.mark.parametrize("entry", HOSTILE_FIXTURES, ids=lambda e: e["fixture_id"])
def test_hostile_fixture_agrees_with_the_real_library(entry: dict[str, Any]) -> None:
    """Where the built-in checker rejects on schema grounds, so must the real one.

    Four hostile properties are digest- or archive-level and invisible to any
    validator; those are expected to be schema-clean, and the assertion is
    inverted for them so the distinction stays explicit rather than assumed.
    """
    if not HAVE_JSONSCHEMA:  # pragma: no cover - depends on the environment
        pytest.skip("jsonschema is not installed; the built-in checker is authoritative")
    beyond_schema = {
        "jobspec_digest_mismatch",
        "artifact_digest_mismatch",
        "manifest_digest_mismatch",
        "undeclared_archive_entry",
        "symlink_archive_entry_refused",
        "attestation_binding_mismatch",
    }
    validator = _jsonschema_validator(_schema_for(entry))
    assert validator is not None
    errors = list(validator.iter_errors(_document(entry)))
    if entry["expected_rejection"]["code"] in beyond_schema:
        assert errors == [], "this property is not a schema property; do not fake it as one"
    else:
        assert errors, "the built-in checker rejected on schema grounds; the real one did not"


def test_hostile_text_is_refused_for_its_control_characters_not_its_content() -> None:
    """The injection strings are recorded evidence, not something to filter out.

    Stripping only the characters that cannot be shown faithfully to a human
    leaves a document that validates — with the prompt injection, the template
    and shell expansions, the traversal string and the forged verdict all still
    in it. That is the intended handling: measured, never obeyed.
    """
    entry = _fixture("hostile_reviewer_and_model_text")
    document = _document(entry)
    note = document["narrative"]["reviewer_note"]

    assert "\u0000" in note
    assert "\u202e" in note
    assert "ignore previous instructions" in note
    assert "${{" in note
    assert "$(cat /etc/passwd)" in note
    assert "../../etc/passwd" in note
    assert '"verdict": "satisfied"' in note

    declawed = json.loads(json.dumps(document))
    # Written as escapes rather than as literal bytes: a NUL and a bidi override
    # are what this test is about, not something to smuggle into a source file.
    forbidden = re.compile(
        "[\\u0000-\\u0008\\u000b\\u000c\\u000e-\\u001f\\u007f"
        "\\u200e\\u200f\\u202a-\\u202e\\u2066-\\u2069]"
    )
    for field in ("agent_summary", "reviewer_note"):
        declawed["narrative"][field] = forbidden.sub("", declawed["narrative"][field])

    assert validate(declawed, REGISTRY[INTAKE_ID]) == []
    assert "ignore previous instructions" in declawed["narrative"]["reviewer_note"]
    assert "accepted_for_review" in declawed["narrative"]["reviewer_note"]


def test_narrative_is_marked_untrusted_in_every_bundle_fixture() -> None:
    for entry in FIXTURES:
        document = _document(entry)
        if document.get("schema_version") != "evidence-intake/1.0.0":
            continue
        assert document["narrative"]["trust_level"] == "untrusted"


# ---------------------------------------------------------------------------
# Outcome vocabulary
# ---------------------------------------------------------------------------


def _outcome_instance(**overrides: Any) -> dict[str, Any]:
    document = _document(_fixture("hostile_verifier_attestation_mismatch"))
    document["verifier_attestation"]["bound_manifest_digest"] = document["bundle_manifest_digest"]
    document.update(overrides)
    return document


@pytest.mark.parametrize("outcome", PERMITTED_OUTCOMES)
def test_outcome_schema_accepts_each_permitted_outcome(outcome: str) -> None:
    assert validate(_outcome_instance(outcome=outcome), REGISTRY[OUTCOME_ID]) == []


@pytest.mark.parametrize("word", FORBIDDEN_OUTCOMES)
def test_outcome_schema_refuses_the_forbidden_vocabulary(word: str) -> None:
    found = validate(_outcome_instance(outcome=word), REGISTRY[OUTCOME_ID])
    assert [v.code for v in found] == ["enum_not_allowed"]
    assert found[0].pointer == "/outcome"


@pytest.mark.parametrize("word", FORBIDDEN_OUTCOMES)
def test_forbidden_vocabulary_cannot_be_smuggled_in_as_an_extra_member(word: str) -> None:
    """additionalProperties: false is what stops `"approved": true` being added."""
    found = validate(_outcome_instance(**{word: True}), REGISTRY[OUTCOME_ID])
    assert [v.as_dict() for v in found] == [
        {"code": "unexpected_property", "pointer": "", "detail": word}
    ]


def test_outcome_schema_pins_the_three_non_negotiable_facts() -> None:
    schema = REGISTRY[OUTCOME_ID]["properties"]
    for name in ("no_merge_performed", "no_deployment_performed", "human_review_required"):
        assert schema[name]["const"] is True
        found = validate(_outcome_instance(**{name: False}), REGISTRY[OUTCOME_ID])
        assert [v.code for v in found] == ["const_mismatch"]


def test_outcome_enum_is_exactly_the_four_supported_values() -> None:
    assert REGISTRY[OUTCOME_ID]["properties"]["outcome"]["enum"] == list(PERMITTED_OUTCOMES)


# ---------------------------------------------------------------------------
# Version pinning
# ---------------------------------------------------------------------------


def _minimal_request() -> dict[str, Any]:
    return {
        "envelope_version": "verifier-envelope/1.0.0",
        "record_type": "request",
        "request_id": "vreq-2026-08-01-0042",
        "nonce": "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
        "evaluation_run_id": "run-2026-08-01-0042",
        "jobspec_digest": sha256_text("jobspec"),
        "candidate_artifact_digests": [sha256_text("artifact")],
        "issued_at": "2026-08-01T09:58:00Z",
    }


def _minimal_result() -> dict[str, Any]:
    return {
        "envelope_version": "verifier-envelope/1.0.0",
        "record_type": "result",
        "request_id": "vreq-2026-08-01-0042",
        "nonce": "0f1e2d3c4b5a69788796a5b4c3d2e1f0",
        "bound_jobspec_digest": sha256_text("jobspec"),
        "bound_artifact_digests": [sha256_text("artifact")],
        "verdict": "satisfied",
        "attestation_digest": sha256_text("attestation"),
        "completed_at": "2026-08-01T10:01:12Z",
    }


VERSION_CASES = [
    ("evidence-intake", INTAKE_ID, "schema_version", "evidence-intake/1.1.0"),
    ("evallab-outcome", OUTCOME_ID, "schema_version", "evallab-outcome/2.0.0"),
    ("jobspec-reference", JOBSPEC_ID, "schema_version", "jobspec-reference/1.0.1"),
    ("verifier-envelope", ENVELOPE_ID, "envelope_version", "verifier-envelope/1.1.0"),
]


@pytest.mark.parametrize(
    ("name", "schema_id", "field", "bumped"), VERSION_CASES, ids=[c[0] for c in VERSION_CASES]
)
def test_a_bumped_version_is_refused_rather_than_loosely_accepted(
    name: str, schema_id: str, field: str, bumped: str
) -> None:
    if schema_id == INTAKE_ID:
        instance = _document(_fixture("valid_single_attempt"))
    elif schema_id == OUTCOME_ID:
        instance = _outcome_instance()
    elif schema_id == JOBSPEC_ID:
        instance = _document(_fixture("valid_single_attempt"))["jobspec_reference"]
    else:
        instance = _minimal_request()

    assert validate(instance, REGISTRY[schema_id]) == []
    instance[field] = bumped
    found = validate(instance, REGISTRY[schema_id])
    assert [v.code for v in found] == ["unsupported_schema_version"]
    assert found[0].pointer == f"/{field}"


# ---------------------------------------------------------------------------
# Verifier envelope
# ---------------------------------------------------------------------------


def test_envelope_accepts_a_minimal_request_and_a_minimal_result() -> None:
    assert validate(_minimal_request(), REGISTRY[ENVELOPE_ID]) == []
    assert validate(_minimal_result(), REGISTRY[ENVELOPE_ID]) == []


@pytest.mark.parametrize(
    "smuggled",
    [
        {"hidden_test_results": [{"test": "test_race", "passed": False}]},
        {"failing_tests": ["test_race"]},
        {"threshold": 0.8},
        {"private_report": "candidate fails the concurrency holdout"},
        {"gold_reference": "def commit_effect(): ..."},
    ],
    ids=["per_test", "test_names", "threshold", "report", "gold"],
)
def test_envelope_result_has_nowhere_to_put_hidden_test_detail(smuggled: dict[str, Any]) -> None:
    """The leak this boundary exists to prevent must fail validation, not be reviewed out."""
    instance = _minimal_result() | smuggled
    found = validate(instance, REGISTRY[ENVELOPE_ID])
    assert [v.code for v in found] == ["unexpected_property"]
    assert found[0].detail == next(iter(smuggled))


def test_envelope_result_carries_no_free_text_and_no_number() -> None:
    """Tightness asserted structurally, not promised in prose.

    Every member of a result is a const, a fixed enum, a digest, a pattern-bound
    identifier, or an array of digests. There is no unconstrained string and no
    numeric member, so there is nowhere to encode a per-test outcome, a score, a
    count or a threshold even in principle.
    """
    result = REGISTRY[ENVELOPE_ID]["$defs"]["result"]["properties"]
    for name, subschema in result.items():
        if "const" in subschema or "enum" in subschema:
            continue
        if subschema.get("type") == "string":
            assert subschema.get("pattern"), f"{name} is an unconstrained string"
            continue
        assert subschema.get("type") == "array", f"{name} is neither constrained nor an array"
        assert subschema["items"] == {"type": "string", "pattern": "^[a-f0-9]{64}$"}


def test_envelope_request_carries_no_evaluation_intent() -> None:
    """A request that expresses what Eval-lab hopes to find invites a shaped answer."""
    request = REGISTRY[ENVELOPE_ID]["$defs"]["request"]["properties"]
    assert set(request) == {
        "envelope_version",
        "record_type",
        "request_id",
        "nonce",
        "evaluation_run_id",
        "jobspec_digest",
        "candidate_artifact_digests",
        "issued_at",
    }


# ---------------------------------------------------------------------------
# Reference-checker behaviours no fixture covers
# ---------------------------------------------------------------------------


def test_unexpected_extra_member_is_detectable_anywhere_in_a_bundle() -> None:
    document = _document(_fixture("valid_single_attempt"))
    document["provenance"]["operator_override"] = "accepted_for_review"
    found = validate(document, REGISTRY[INTAKE_ID])
    assert [v.as_dict() for v in found] == [
        {"code": "unexpected_property", "pointer": "/provenance", "detail": "operator_override"}
    ]


def test_out_of_order_attempt_lineage_is_detected() -> None:
    """Ordering is not expressible in JSON Schema, so the checker owns it."""
    entry = _fixture("valid_bounded_retry")
    document = _document(entry)
    document["attempts"] = [document["attempts"][2], *document["attempts"][:2]]
    document["manifest_digest"] = recompute_manifest_digest(document)
    found = check_bundle(document, entry["materialisation"])
    assert [v.code for v in found] == [
        "attempt_lineage_disordered",
        "attempt_lineage_disordered",
        "attempt_lineage_disordered",
        "attempt_retry_flag_inconsistent",
    ]


def test_a_test_summary_that_cannot_be_reconciled_is_detected() -> None:
    entry = _fixture("valid_single_attempt")
    document = _document(entry)
    document["visible_test_results"]["final"]["passed"] = 11
    document["manifest_digest"] = recompute_manifest_digest(document)
    found = check_bundle(document, entry["materialisation"])
    assert [v.as_dict() for v in found] == [
        {
            "code": "test_counts_inconsistent",
            "pointer": "/visible_test_results/final/total",
            "detail": None,
        }
    ]


def test_manifest_digest_binds_every_field_not_just_the_narrative() -> None:
    entry = _fixture("valid_single_attempt")
    for field, value in (
        ("bundle_id", "wb-bundle-9999"),
        ("produced_at", "2026-08-01T23:59:59Z"),
    ):
        document = _document(entry)
        document[field] = value
        found = check_bundle(document, entry["materialisation"])
        assert [v.code for v in found] == ["manifest_digest_mismatch"]


# ---------------------------------------------------------------------------
# Nothing credential-shaped anywhere in the corpus
# ---------------------------------------------------------------------------

CREDENTIAL_PATTERNS = (
    ("openai_key", r"sk-[A-Za-z0-9_\-]{16,}"),
    ("github_token", r"gh[pousr]_[A-Za-z0-9]{20,}"),
    ("github_pat", r"github_pat_[A-Za-z0-9_]{20,}"),
    ("aws_access_key", r"AKIA[0-9A-Z]{16}"),
    ("slack_token", r"xox[baprs]-[A-Za-z0-9\-]{10,}"),
    ("private_key", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("bearer_header", r"(?i)authorization\s*:\s*bearer\s+\S{16,}"),
    (
        "assigned_secret",
        r"(?i)(api[_\-]?key|secret|password|token)\s*[=:]\s*\"?[A-Za-z0-9_\-]{16,}",
    ),
)


@pytest.mark.parametrize("path", sorted(FIXTURE_DIR.rglob("*.json")), ids=lambda p: p.name)
def test_no_fixture_contains_a_credential_shaped_string(path: Path) -> None:
    """A fixture is committed, public, and copied by whoever implements against it.

    Nothing in one may look like a live credential — not because a fake would
    work, but because a fake that looks real gets rotated, reported, or pasted
    into a real configuration by someone moving fast.
    """
    text = path.read_text(encoding="utf-8")
    hits = [name for name, pattern in CREDENTIAL_PATTERNS if re.search(pattern, text)]
    assert hits == [], f"{path.name} contains credential-shaped text: {hits}"


@pytest.mark.parametrize("path", _schema_files(), ids=lambda p: p.name)
def test_no_schema_contains_a_credential_shaped_string(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    hits = [name for name, pattern in CREDENTIAL_PATTERNS if re.search(pattern, text)]
    assert hits == []


def test_no_fixture_or_schema_names_the_verifier_repository() -> None:
    """The verifier repository is out of bounds for every workstream in this milestone."""
    for path in [*_schema_files(), *sorted(FIXTURE_DIR.rglob("*.json"))]:
        assert "Eval-lab-verifier" not in path.read_text(encoding="utf-8")
