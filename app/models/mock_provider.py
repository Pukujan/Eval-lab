"""Three deterministic mock models, registered as a LiteLLM custom provider.

Written against the pattern LiteLLM ships in
``litellm/proxy/example_config_yaml/custom_handler.py``: subclass
:class:`litellm.CustomLLM`, implement ``completion``/``acompletion``, and register
the instance through ``litellm_settings.custom_provider_map`` (ADR-0004).

This is emphatically **not** a custom provider SDK. It is a plugin hanging off
LiteLLM's own documented extension point; LiteLLM still owns routing, the request
and response schema, and normalisation.

Determinism is by construction: every response is a pure function of
``(model_name, sha256(canonicalised messages))``. No clock, no RNG, no network,
no credentials. The same request produces byte-identical output forever, which is
what makes a benchmark result mean anything.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import litellm
from litellm import CustomLLM
from litellm.types.llms.custom_llm import CustomLLMItem
from litellm.types.utils import Choices, Message, ModelResponse, Usage

#: Fixed creation timestamp. A real clock would make responses non-reproducible
#: and would make byte-identical comparison impossible.
FIXED_CREATED = 1_700_000_000

MOCK_MODEL_NAMES: tuple[str, ...] = ("mock-analyst", "mock-skeptic", "mock-minimalist")


def _canonical_request_digest(model: str, messages: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        {"model": model, "messages": messages}, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _extract_task(messages: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Read the structured task out of the last user message.

    Tasks are handed over as JSON rather than prose so the mock can dispatch
    deterministically instead of pattern-matching English.
    """
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if not isinstance(content, str):
            continue
        try:
            payload = json.loads(content)
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict) and "task_type" in payload:
            return str(payload["task_type"]), payload
    return "unknown", {}


# ---------------------------------------------------------------------------
# Response bodies. Each model has a stable, distinguishable investigative style.
# ---------------------------------------------------------------------------

_HYPOTHESIS_LIBRARY: dict[str, list[dict[str, Any]]] = {
    # Three causally distinct mechanisms, each falsifiable.
    "mock-analyst": [
        {
            "hypothesis_id": "H-1",
            "mechanism_class": "check_then_write_race",
            "causal_mechanism": (
                "The duplicate check and the commit are separate steps with no "
                "exclusivity between them, so two concurrent workers can both "
                "observe 'not yet processed' and both proceed to commit."
            ),
            "assumptions": [
                {
                    "assumption_id": "A-1",
                    "statement": "Two workers can hold the same job id at once.",
                },
                {"assumption_id": "A-2", "statement": "Nothing between check and write is atomic."},
            ],
            "predicted_observations": [
                "Concurrent delivery produces two committed rows for one job id.",
                "Sequential redelivery produces exactly one row.",
            ],
            "falsification_condition": (
                "Falsified if forcing both workers past the duplicate check still "
                "yields exactly one committed row."
            ),
            "proposed_probe_id": "P-concurrent-delivery",
        },
        {
            "hypothesis_id": "H-2",
            "mechanism_class": "missing_duplicate_check",
            "causal_mechanism": (
                "The processor never checks whether a job was already handled, so "
                "every redelivery reprocesses unconditionally."
            ),
            "assumptions": [
                {
                    "assumption_id": "A-3",
                    "statement": "No duplicate check exists in the commit path.",
                }
            ],
            "predicted_observations": [
                "Sequential redelivery also produces two committed rows.",
            ],
            "falsification_condition": (
                "Falsified if sequential redelivery produces exactly one committed row."
            ),
            "proposed_probe_id": "P-sequential-redelivery",
        },
        {
            "hypothesis_id": "H-3",
            "mechanism_class": "queue_delivery_defect",
            "causal_mechanism": (
                "The queue violates its contract and delivers a job twice when it "
                "should deliver it once; the consumer is blameless."
            ),
            "assumptions": [
                {"assumption_id": "A-4", "statement": "Delivery is intended to be exactly-once."}
            ],
            "predicted_observations": [
                "Duplication is visible at the delivery layer independent of the consumer.",
            ],
            "falsification_condition": (
                "Falsified if the declared delivery model is at-least-once, making "
                "redelivery correct queue behaviour."
            ),
            "proposed_probe_id": "P-delivery-contract",
        },
    ],
    "mock-skeptic": [
        {
            "hypothesis_id": "H-1",
            "mechanism_class": "check_then_write_race",
            "causal_mechanism": (
                "Two workers interleave between the duplicate check and the commit; "
                "the store offers an atomic claim that the processor does not take."
            ),
            "assumptions": [
                {"assumption_id": "A-1", "statement": "The commit path has no exclusivity."}
            ],
            "predicted_observations": [
                "Both workers report having committed.",
                "The external effect counter reaches two for one job id.",
            ],
            "falsification_condition": (
                "Falsified if only one worker ever reports a commit under forced concurrency."
            ),
            "proposed_probe_id": "P-concurrent-delivery",
        },
        {
            "hypothesis_id": "H-2",
            "mechanism_class": "non_idempotent_effect",
            "causal_mechanism": (
                "The external effect is not idempotent, so even a correct single "
                "commit path would double the externally visible outcome on retry."
            ),
            "assumptions": [{"assumption_id": "A-2", "statement": "The effect has no dedupe key."}],
            "predicted_observations": [
                "Effect count exceeds committed row count in some runs.",
            ],
            "falsification_condition": (
                "Falsified if effect count and committed row count always agree."
            ),
            "proposed_probe_id": "P-effect-counter",
        },
        {
            "hypothesis_id": "H-3",
            "mechanism_class": "read_path_duplication",
            "causal_mechanism": (
                "Only one result is stored; the read API joins incorrectly and reports it twice."
            ),
            "assumptions": [{"assumption_id": "A-3", "statement": "Storage holds a single row."}],
            "predicted_observations": [
                "Raw stored rows number one while the read API reports two.",
            ],
            "falsification_condition": ("Falsified if the raw row count is itself two."),
            "proposed_probe_id": "P-raw-rows",
        },
    ],
    # Deliberately weaker: two of its three hypotheses share a mechanism class,
    # so the diversity check has something real to catch.
    "mock-minimalist": [
        {
            "hypothesis_id": "H-1",
            "mechanism_class": "check_then_write_race",
            "causal_mechanism": "Two workers process the same job at the same time.",
            "assumptions": [{"assumption_id": "A-1", "statement": "Concurrency is possible."}],
            "predicted_observations": ["Two rows appear."],
            "falsification_condition": "Falsified if only one row appears under concurrency.",
            "proposed_probe_id": "P-concurrent-delivery",
        },
        {
            "hypothesis_id": "H-2",
            "mechanism_class": "check_then_write_race",
            "causal_mechanism": "A locking problem lets two workers in at once.",
            "assumptions": [{"assumption_id": "A-2", "statement": "Locking is absent."}],
            "predicted_observations": ["Two rows appear."],
            "falsification_condition": "Falsified if only one row appears.",
            "proposed_probe_id": "P-concurrent-delivery",
        },
        {
            "hypothesis_id": "H-3",
            "mechanism_class": "missing_duplicate_check",
            "causal_mechanism": "There is no duplicate check.",
            "assumptions": [{"assumption_id": "A-3", "statement": "No check exists."}],
            "predicted_observations": ["Sequential redelivery duplicates too."],
            "falsification_condition": "Falsified if sequential redelivery commits once.",
            "proposed_probe_id": "P-sequential-redelivery",
        },
    ],
}

_REPAIR_LIBRARY: dict[str, list[dict[str, Any]]] = {
    "default": [
        {
            "candidate_id": "C-claim",
            "hypothesis_id": "H-1",
            "strategy": "establish_invariant",
            "description": (
                "Take an atomic claim on the job id before performing any "
                "irreversible work, so exclusivity is decided by the database."
            ),
            "claims_mechanism_addressed": True,
            "patch_source": "reference",
        },
        {
            "candidate_id": "C-dedupe-read",
            "hypothesis_id": "H-3",
            "strategy": "symptom_suppression",
            "description": (
                "Group results by job id on read so the duplicate stops being visible to callers."
            ),
            "claims_mechanism_addressed": False,
            "patch_source": "ducttape",
        },
    ]
}


def _build_content(model: str, messages: list[dict[str, Any]]) -> str:
    task_type, payload = _extract_task(messages)
    digest = _canonical_request_digest(model, messages)
    base = model.split("/")[-1]

    if task_type == "generate_hypotheses":
        hypotheses = _HYPOTHESIS_LIBRARY.get(base, _HYPOTHESIS_LIBRARY["mock-analyst"])
        body: dict[str, Any] = {"task_type": task_type, "hypotheses": hypotheses}
    elif task_type == "design_probes":
        body = {
            "task_type": task_type,
            "probes": [
                {
                    "probe_id": "P-concurrent-delivery",
                    "hypothesis_id": "H-1",
                    "description": "Force both workers past the duplicate check, then commit.",
                    "implementation": "fixtures.duplicate-job-processing.probe:run_probe",
                    "discriminates": ["H-1", "H-2"],
                },
                {
                    "probe_id": "P-sequential-redelivery",
                    "hypothesis_id": "H-2",
                    "description": "Redeliver the job after the first delivery completed.",
                    "implementation": "app.activities.probes:sequential_redelivery_probe",
                    "discriminates": ["H-2"],
                },
                {
                    "probe_id": "P-delivery-contract",
                    "hypothesis_id": "H-3",
                    "description": "Read the declared delivery model from INVARIANTS.md.",
                    "implementation": "app.activities.probes:delivery_contract_probe",
                    "discriminates": ["H-3"],
                },
            ],
        }
    elif task_type == "generate_repair_candidates":
        body = {"task_type": task_type, "candidates": _REPAIR_LIBRARY["default"]}
    else:
        body = {
            "task_type": task_type or "unknown",
            "note": "no structured task recognised",
            "request_digest": digest,
        }

    # The digest travels with every response: it is what a test asserts on to
    # prove the mock keyed off the request rather than ignoring it.
    body["request_digest"] = digest
    body["responding_identity"] = base
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def _build_response(model: str, messages: list[dict[str, Any]]) -> ModelResponse:
    content = _build_content(model, messages)
    digest = _canonical_request_digest(model, messages)

    # Token-like usage derived from lengths — deterministic, and enough for
    # Promptfoo to report comparative usage without inventing numbers.
    prompt_tokens = sum(len(str(m.get("content", ""))) for m in messages) // 4
    completion_tokens = len(content) // 4

    return ModelResponse(
        id=f"mockresp-{digest[:24]}",
        created=FIXED_CREATED,
        model=model,
        object="chat.completion",
        choices=[
            Choices(
                index=0,
                message=Message(role="assistant", content=content),
                finish_reason="stop",
            )
        ],
        usage=Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


class ReliabilityMockLLM(CustomLLM):
    """Deterministic, credential-free mock models."""

    def completion(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return _build_response(kwargs.get("model", "mock-analyst"), kwargs.get("messages") or [])

    async def acompletion(self, *args: Any, **kwargs: Any) -> ModelResponse:
        return _build_response(kwargs.get("model", "mock-analyst"), kwargs.get("messages") or [])


#: The instance referenced by ``custom_provider_map`` in the proxy config.
reliability_mock = ReliabilityMockLLM()


def register_in_process() -> None:
    """Register the provider for in-process use (tests, Promptfoo bridge).

    The application itself always goes over HTTP to the proxy; this exists so a
    unit test can exercise the handler contract without a running service.
    """
    entry: CustomLLMItem = {
        "provider": "reliability-mock",
        "custom_handler": reliability_mock,
    }
    if entry not in litellm.custom_provider_map:
        litellm.custom_provider_map = [*litellm.custom_provider_map, entry]
