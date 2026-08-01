"""The frozen evaluation-service alias snapshot.

Task 2B evaluates a list of model aliases. Where that list comes from decides
whether the campaign means anything, so it is a first-class, hashed artifact
rather than a constant in code or a list in a document.

**Why a hardcoded list is not acceptable.** An earlier version of this scaffold
carried eleven aliases "observed on the gateway", with an opt-in flag for anything
outside them. Both were wrong. The gateway now exposes many more aliases than
that; the production inventory is not the evaluation service's inventory; and an
opt-in flag turns "this alias was not in the frozen set" from a hard stop into a
box someone ticks at 2am. The list in code is now gone, and so is the flag.

**Why the snapshot must name the evaluation service.** The production gateway
retries five times at both the SDK and router layers, pools some aliases across up
to three upstream routes, cools failing routes down, drops unsupported parameters
silently, and queues requests so a 429 never surfaces. Every one of those turns a
failure into a slow success. A snapshot taken from production would look correct
and describe a service whose numbers cannot be attributed, so a production URL is
refused here rather than warned about.

**Why the hash.** The alias list is the one input that, if it changes silently,
makes every result in the campaign describe a different experiment. The snapshot
therefore carries a SHA-256 over its own normalised alias list, and loading it
recomputes that hash. A snapshot whose recorded hash does not match its own
contents is refused — it is either edited or corrupt, and neither is safe to
evaluate against.

Order is preserved exactly as frozen. The list is never sorted, de-duplicated by
normalisation, case-folded, or trimmed on load: aliases are opaque strings the
gateway chose, several contain spaces and brackets, and each of those operations
would silently produce a different experiment from the one that was frozen.

Nothing here classifies an alias as frontier or otherwise. That is a research
decision recorded *in* the snapshot by the human who froze it, not one this module
is entitled to make.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Final

#: The only base URL a snapshot may name. The evaluation service exists precisely
#: because production is not evidence-valid; accepting a production snapshot would
#: defeat the reason the second service was deployed.
EVALUATION_SERVICE_URL: Final[str] = "https://litellm-eval-production.up.railway.app"

#: Deliberately invalid alias the evaluation service exposes so a validator can
#: prove failures surface fast rather than falling back. It routes at a
#: nonexistent upstream, so it must never be evaluated as if it were a model.
CANARY_INVALID_ALIAS: Final[str] = "__canary_invalid"

#: Aliases that are not real models and must be excluded from any benchmark.
NON_MODEL_ALIASES: Final[frozenset[str]] = frozenset({CANARY_INVALID_ALIAS})

SNAPSHOT_VERSION: Final[int] = 1

REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "snapshot_version",
    "retrieved_at",
    "source",
    "method",
    "evaluation_service_url",
    "evaluation_service_identifier",
    "aliases",
    "sha256",
)


class SnapshotError(ValueError):
    """The alias snapshot is not one this harness will evaluate against."""


def normalise_alias_list(aliases: tuple[str, ...]) -> str:
    """The exact bytes the hash covers.

    Newline-separated, in frozen order, with a trailing newline. Deliberately not
    JSON: JSON has whitespace and key-ordering freedom, so two encoders could
    produce different bytes for the same list and the hash would stop being a
    property of the list.
    """
    return "".join(f"{alias}\n" for alias in aliases)


def alias_list_sha256(aliases: tuple[str, ...]) -> str:
    return hashlib.sha256(normalise_alias_list(aliases).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FrozenAliasSnapshot:
    """One retrieval of the evaluation service's alias list, frozen and hashed."""

    snapshot_version: int
    #: UTC ISO-8601. When the list was read off the service, not when it was written.
    retrieved_at: str
    #: What was read — e.g. the endpoint or the validator artifact.
    source: str
    #: How it was read, in enough detail for someone else to repeat it.
    method: str
    evaluation_service_url: str
    #: Which deployment/config produced this list. Without it a snapshot names a
    #: list but not the thing that served it, and a redeploy is invisible.
    evaluation_service_identifier: str
    aliases: tuple[str, ...]
    sha256: str
    #: Aliases seen on the service and deliberately left out, each with a reason.
    excluded: tuple[tuple[str, str], ...] = ()
    #: Optional per-alias classification recorded by the human who froze the list.
    classification: tuple[tuple[str, str], ...] = ()
    notes: str = ""

    @property
    def computed_sha256(self) -> str:
        return alias_list_sha256(self.aliases)

    def as_document(self) -> dict[str, Any]:
        return {
            "snapshot_version": self.snapshot_version,
            "retrieved_at": self.retrieved_at,
            "source": self.source,
            "method": self.method,
            "evaluation_service_url": self.evaluation_service_url,
            "evaluation_service_identifier": self.evaluation_service_identifier,
            "alias_count": len(self.aliases),
            "aliases": list(self.aliases),
            "sha256": self.sha256,
            "excluded": [{"alias": a, "reason": r} for a, r in self.excluded],
            "classification": [{"alias": a, "class": c} for a, c in self.classification],
            "notes": self.notes,
        }


def _require_text(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SnapshotError(f"snapshot field {key!r} must be a non-empty string, got {value!r}")
    return value


def _validate_timestamp(raw: str) -> str:
    """Accept only an explicit UTC instant.

    A naive timestamp is ambiguous by exactly the amount that matters when
    correlating a snapshot against a deployment.
    """
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise SnapshotError(
            f"retrieved_at {raw!r} is not an ISO-8601 timestamp; write it as UTC, "
            "for example 2026-08-01T18:30:00Z"
        ) from exc
    if parsed.tzinfo is None:
        raise SnapshotError(
            f"retrieved_at {raw!r} has no timezone; a naive timestamp cannot be tied to "
            "a deployment window, so UTC must be explicit"
        )
    return raw


def _validate_aliases(raw: object) -> tuple[str, ...]:
    from app.models.sequential_plan import PlanError, validate_alias

    if not isinstance(raw, list) or not raw:
        raise SnapshotError("snapshot field 'aliases' must be a non-empty JSON array")
    try:
        aliases = tuple(validate_alias(alias) for alias in raw)
    except PlanError as exc:
        raise SnapshotError(f"snapshot contains an unusable alias: {exc}") from exc

    duplicates = sorted({a for a in aliases if aliases.count(a) > 1})
    if duplicates:
        raise SnapshotError(
            f"snapshot lists {duplicates} more than once; evidence is written per alias "
            "and a repeat would blend two models' records into one"
        )
    present_non_models = sorted(set(aliases) & NON_MODEL_ALIASES)
    if present_non_models:
        raise SnapshotError(
            f"snapshot includes non-model alias(es) {present_non_models}. "
            f"{CANARY_INVALID_ALIAS} routes at a nonexistent upstream so that a "
            "validator can prove failures surface; evaluating it as a model would "
            "record a fabricated failure"
        )
    return aliases


def load_snapshot(path: Path | str) -> FrozenAliasSnapshot:
    """Read and fully validate a frozen snapshot, or raise :class:`SnapshotError`."""
    path = Path(path)
    if not path.is_file():
        raise SnapshotError(
            f"no frozen alias snapshot at {path}. Task 2B will not run against an "
            "ad-hoc model list: freeze the evaluation service's aliases first"
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise SnapshotError(f"{path} is not parseable JSON ({exc})") from exc
    if not isinstance(payload, dict):
        raise SnapshotError(f"{path} is a JSON {type(payload).__name__}, not an object")

    missing = [key for key in REQUIRED_FIELDS if key not in payload]
    if missing:
        raise SnapshotError(
            f"{path} is missing required field(s) {missing}. A snapshot must record "
            "what was retrieved, when, from where, how, from which deployment, and "
            "the hash of the list itself"
        )

    if payload["snapshot_version"] != SNAPSHOT_VERSION:
        raise SnapshotError(
            f"snapshot_version is {payload['snapshot_version']!r}, this harness reads "
            f"{SNAPSHOT_VERSION}"
        )

    url = _require_text(payload, "evaluation_service_url").rstrip("/")
    if url != EVALUATION_SERVICE_URL:
        raise SnapshotError(
            f"snapshot names {url!r}. Only the evaluation service is accepted:\n"
            f"  {EVALUATION_SERVICE_URL}\n"
            "The production gateway retries at two layers, pools some aliases across "
            "multiple upstream routes, cools failing routes down, drops parameters "
            "silently and queues requests — a snapshot from it would look correct and "
            "describe a service whose numbers cannot be attributed"
        )

    aliases = _validate_aliases(payload["aliases"])
    recorded_hash = _require_text(payload, "sha256").lower()
    computed = alias_list_sha256(aliases)
    if recorded_hash != computed:
        raise SnapshotError(
            f"{path} records sha256 {recorded_hash} but its alias list hashes to "
            f"{computed}. The snapshot has been edited or is corrupt; it is not the "
            "list that was frozen, so it is not the experiment that was agreed"
        )

    excluded_raw = payload.get("excluded", [])
    if not isinstance(excluded_raw, list):
        raise SnapshotError("snapshot field 'excluded' must be an array when present")
    excluded: list[tuple[str, str]] = []
    for entry in excluded_raw:
        if not isinstance(entry, dict) or "alias" not in entry or "reason" not in entry:
            raise SnapshotError(
                "each 'excluded' entry needs an 'alias' and a 'reason'; an exclusion "
                "without a stated reason is a silent omission"
            )
        excluded.append((str(entry["alias"]), str(entry["reason"])))

    classification_raw = payload.get("classification", [])
    if not isinstance(classification_raw, list):
        raise SnapshotError("snapshot field 'classification' must be an array when present")
    classification = [
        (str(entry["alias"]), str(entry["class"]))
        for entry in classification_raw
        if isinstance(entry, dict) and "alias" in entry and "class" in entry
    ]

    return FrozenAliasSnapshot(
        snapshot_version=SNAPSHOT_VERSION,
        retrieved_at=_validate_timestamp(_require_text(payload, "retrieved_at")),
        source=_require_text(payload, "source"),
        method=_require_text(payload, "method"),
        evaluation_service_url=url,
        evaluation_service_identifier=_require_text(payload, "evaluation_service_identifier"),
        aliases=aliases,
        sha256=computed,
        excluded=tuple(excluded),
        classification=tuple(classification),
        notes=str(payload.get("notes", "")),
    )
