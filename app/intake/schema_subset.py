"""The bounded JSON-Schema subset used by Eval-lab's frozen public contracts.

The contract tests already prove that the released schemas use only this subset.
Keeping the implementation here means production intake does not rely on
``jsonschema`` being present only as a transitive model-gateway dependency.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parents[2] / "contracts" / "schemas"


@dataclass(frozen=True)
class SchemaViolation:
    code: str
    pointer: str
    detail: str | None = None


def load_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        document = json.loads(path.read_text(encoding="utf-8"))
        registry[str(document["$id"])] = document
    return registry


REGISTRY = load_registry()


def schema_by_title(title: str) -> dict[str, Any]:
    for schema in REGISTRY.values():
        if schema.get("title") == title:
            return schema
    raise KeyError(title)


def _escape(token: str) -> str:
    return token.replace("~", "~0").replace("/", "~1")


def _json_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            _json_equal(left[key], right[key]) for key in left
        )
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
    raise AssertionError(f"unsupported schema type {expected!r}")


def _resolve(ref: str, root: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
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
    out: list[SchemaViolation],
) -> None:
    if "$ref" in schema:
        target, target_root = _resolve(schema["$ref"], root)
        _validate(instance, target, pointer, target_root, out)

    if "oneOf" in schema:
        attempts: list[list[SchemaViolation]] = []
        for branch in schema["oneOf"]:
            found: list[SchemaViolation] = []
            _validate(instance, branch, pointer, root, found)
            attempts.append(found)
        matching = [index for index, found in enumerate(attempts) if not found]
        if len(matching) == 1:
            pass
        elif len(matching) > 1:
            out.append(SchemaViolation("one_of_ambiguous", pointer))
        else:
            out.extend(min(attempts, key=len))

    if "type" in schema and not _type_matches(instance, schema["type"]):
        out.append(SchemaViolation("type_mismatch", pointer, schema["type"]))
        return

    if "const" in schema and not _json_equal(instance, schema["const"]):
        code = "const_mismatch"
        if pointer.endswith(("/schema_version", "/envelope_version")):
            code = "unsupported_schema_version"
        expected = schema["const"]
        out.append(SchemaViolation(code, pointer, expected if isinstance(expected, str) else None))

    if "enum" in schema and not any(_json_equal(instance, option) for option in schema["enum"]):
        out.append(SchemaViolation("enum_not_allowed", pointer))

    if isinstance(instance, str):
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            out.append(SchemaViolation("pattern_mismatch", pointer))
        if "minLength" in schema and len(instance) < schema["minLength"]:
            out.append(SchemaViolation("string_length_out_of_range", pointer))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            out.append(SchemaViolation("string_length_out_of_range", pointer))

    if isinstance(instance, int | float) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            out.append(SchemaViolation("value_out_of_range", pointer))
        if "maximum" in schema and instance > schema["maximum"]:
            out.append(SchemaViolation("value_out_of_range", pointer))

    if isinstance(instance, dict):
        for name in schema.get("required", []):
            if name not in instance:
                out.append(SchemaViolation("required_property_missing", pointer, name))
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for name in instance:
                if name not in properties:
                    out.append(SchemaViolation("unexpected_property", pointer, name))
        for name, subschema in properties.items():
            if name in instance:
                _validate(
                    instance[name],
                    subschema,
                    f"{pointer}/{_escape(name)}",
                    root,
                    out,
                )

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            out.append(SchemaViolation("array_length_out_of_range", pointer))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            out.append(SchemaViolation("array_length_out_of_range", pointer))
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True) for item in instance]
            if len(set(encoded)) != len(encoded):
                out.append(SchemaViolation("array_items_not_unique", pointer))
        if "items" in schema:
            for index, item in enumerate(instance):
                _validate(item, schema["items"], f"{pointer}/{index}", root, out)


def validate(instance: Any, schema: dict[str, Any]) -> tuple[SchemaViolation, ...]:
    found: list[SchemaViolation] = []
    _validate(instance, schema, "", schema, found)
    return tuple(found)
