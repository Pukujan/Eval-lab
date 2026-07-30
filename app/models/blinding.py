"""Model identity blinding.

Solver, critic, verifier and comparison roles see a pseudonym and nothing else.
Real identities live in ``privileged.db`` and are written there by the harness,
never by the workflow.

Egress checking is the part that actually earns its keep. Keeping vendor names out
of the store is easy; keeping them out of a prompt that some node assembled from
config is not, so :func:`assert_blinded` scans outbound payloads and raises before
the request leaves the process.
"""

from __future__ import annotations

import random
import re
import secrets
from dataclasses import dataclass

from app.domain.schemas import AnonymousModelIdentity, ModelRole, PrivilegedModelIdentity

#: Vendor and family tokens that must never appear in a blinded payload. Matched
#: case-insensitively on word boundaries.
VENDOR_TOKENS: tuple[str, ...] = (
    "openai",
    "gpt",
    "anthropic",
    "claude",
    "google",
    "gemini",
    "meta",
    "llama",
    "mistral",
    "cohere",
    "deepseek",
    "qwen",
    "zhipu",
    "glm",
    "ollama",
    "azure",
    "bedrock",
)

_TOKEN_PATTERN = re.compile(
    r"(?<![a-z0-9])(" + "|".join(re.escape(t) for t in VENDOR_TOKENS) + r")(?![a-z0-9])",
    re.IGNORECASE,
)


class IdentityLeakError(RuntimeError):
    """Raised when a payload about to leave the process names a real model."""


@dataclass(frozen=True)
class BlindingResult:
    """A run's blinding state: what roles see, and what it really was."""

    anonymous: tuple[AnonymousModelIdentity, ...]
    privileged: tuple[PrivilegedModelIdentity, ...]

    def pseudonym_for(self, role: ModelRole) -> str:
        for identity in self.anonymous:
            if identity.role is role:
                return identity.pseudonym
        raise KeyError(f"no pseudonym assigned for role {role}")


def generate_pseudonym() -> str:
    """A fresh, unpredictable pseudonym of the form ``model-<8 hex>``."""
    return f"model-{secrets.token_hex(4)}"


def blind_models(
    assignments: tuple[tuple[ModelRole, str, str, str], ...],
    run_seed: int,
) -> BlindingResult:
    """Assign pseudonyms and randomise presentation order.

    ``assignments`` is ``(role, vendor, model_identifier, endpoint)`` tuples.

    Order is shuffled with a run-seeded PRNG: reproducible for a given run id, and
    unpredictable across runs. A fixed order would let a reader learn which slot is
    which vendor after a couple of runs, which defeats the exercise.
    """
    shuffled = list(assignments)
    # S311: `random` is correct here and `secrets` would be wrong. Presentation
    # order must be REPRODUCIBLE for a given run id so a run can be replayed from
    # its record; it is not a secret. The values that must be unpredictable —
    # the pseudonyms themselves — come from `secrets.token_hex` above.
    random.Random(run_seed).shuffle(shuffled)  # noqa: S311

    anonymous: list[AnonymousModelIdentity] = []
    privileged: list[PrivilegedModelIdentity] = []

    for order, (role, vendor, model_identifier, endpoint) in enumerate(shuffled):
        pseudonym = generate_pseudonym()
        anonymous.append(
            AnonymousModelIdentity(pseudonym=pseudonym, role=role, presentation_order=order)
        )
        privileged.append(
            PrivilegedModelIdentity(
                pseudonym=pseudonym,
                vendor=vendor,
                model_identifier=model_identifier,
                # Overwritten with the value read back from the response once a
                # call has actually been made; the alias is never trusted.
                resolved_model_identifier=model_identifier,
                endpoint=endpoint,
            )
        )

    return BlindingResult(anonymous=tuple(anonymous), privileged=tuple(privileged))


def find_identity_leaks(payload: str) -> tuple[str, ...]:
    """Vendor/family tokens present in ``payload``."""
    return tuple(sorted({match.group(1).lower() for match in _TOKEN_PATTERN.finditer(payload)}))


def assert_blinded(payload: str, *, context: str = "payload") -> None:
    """Raise :class:`IdentityLeakError` if ``payload`` names a real model.

    Applied to outbound prompts and to span attributes before export — the two
    places a real identity can escape without anyone writing it to a database.
    """
    leaks = find_identity_leaks(payload)
    if leaks:
        raise IdentityLeakError(
            f"{context} contains real model identity tokens: {', '.join(leaks)}"
        )


def normalise_response(content: str) -> str:
    """Flatten vendor-characteristic response shape.

    Blinding names is not enough if one vendor always wraps JSON in a fenced code
    block and another never does — the shape itself is a fingerprint.
    """
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:] if lines and lines[0].startswith("```") else lines
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text
