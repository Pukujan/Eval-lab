"""Bounded, non-retrying, one-model-at-a-time access to the CKFF gateway.

This is the Task 2B egress path. It is written to be boring and refusable: every
branch that could turn an unknown state into a usable-looking result raises
instead.

**Why raw ``httpx`` and not LiteLLM.** ``app/models/gateway.py`` goes through
LiteLLM because for the mock provider LiteLLM's dispatch and response
normalisation are the feature. Here they are the hazard: the LiteLLM client and
router own ``num_retries``, cooldowns, and model-group failover, and any of those
would silently repair the exact condition Task 2B is trying to measure. A run
whose latency includes an invisible second attempt, or whose answer came from a
second model, produces evidence that reads as clean and is not. So this path uses
``httpx`` directly, configures the connection-retry count to zero explicitly, and
then *asserts* the configured value rather than trusting the keyword argument —
see :func:`assert_no_client_retry`. ``httpx`` has no request-level retry at all
(it ships nothing like ``urllib3``'s ``Retry``); the only retry it can do is
``httpcore``'s connection retry, which is what the assertion reads.

**Retry ownership.** Zero here is not "no retries anywhere". Temporal owns every
visible retry, as it does everywhere else in this repository (ADR-0002,
ADR-0004). One retry layer, named, at the level that records its own attempts. A
second layer inside the client would be unrecorded and would corrupt the
attribution.

**No substitution, ever.** The alias asked for and the ``model`` the gateway
echoes back are compared byte-for-byte, and a difference — including a missing or
empty value — aborts the run. There is deliberately no code path that reaches for
another model when one fails; a result attributed to the wrong model is worse than
no result, because it still looks like a result.

**Model output is untrusted input.** It is never evaluated, executed,
interpolated into a shell command, used to build a filesystem path, parsed into a
decision, or allowed to influence which model is called next. It is measured and
hashed. :class:`CallRecord` has no field carrying the text, which is the enforcing
mechanism rather than a promise: a caller cannot act on content it never receives.
That is a real limitation and is stated as one — this path establishes reachability
and attribution, not answer quality.

**Nothing secret leaves.** Prompts come only from the in-repository catalogue in
:mod:`app.models.sequential_plan`; free-form text is refused. The credential is
held in a private attribute, never logged, never placed in an evidence document,
and kept out of ``repr``. Evidence records metadata and a SHA-256 of the content,
following ``app/evidence`` conventions.

Nothing in this module claims a model is calibrated, reliable, or ready for
anything. It records what was asked, what answered, and under which bounds.
"""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Final

import httpx

from app.models.blinding import assert_blinded
from app.models.sequential_plan import (
    DEFAULT_PROMPT_ID,
    RunLimits,
    SequentialRunPlan,
    alias_slug,
    assert_execution_allowed,
    get_prompt,
    validate_alias,
)

#: The number of times this client re-attempts anything. Zero, by construction.
CLIENT_RETRIES: Final[int] = 0

#: Connect phase bound, folded under the per-request timeout. Separate only so a
#: gateway that accepts the TCP connection and then stalls is still bounded by the
#: read timeout rather than by the connect timeout.
CONNECT_TIMEOUT_SECONDS: Final[float] = 10.0

#: Response headers copied into evidence. An allowlist rather than "everything
#: except secrets": a denylist would have to anticipate every header a proxy might
#: add, and the first one it failed to anticipate would be in an artifact.
RECORDED_RESPONSE_HEADERS: Final[tuple[str, ...]] = (
    "x-request-id",
    "x-litellm-call-id",
    "x-litellm-model-id",
    "x-litellm-version",
)

#: Shapes that must never appear in an outbound prompt or an evidence document.
#: Not a claim of completeness — the real control is that prompts come from a
#: fixed catalogue and evidence carries hashes. This is the second layer.
SECRET_SHAPED_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"\bBearer\s+\S{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{12,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


# ---------------------------------------------------------------------------
# Errors. Each names a specific refusal so a reader of a failed run can tell
# "the harness would not proceed" apart from "the model did badly".
# ---------------------------------------------------------------------------


class CkffClientError(RuntimeError):
    """Base class: the client refused to produce or accept a result."""


class ClientConfigurationError(CkffClientError):
    """The HTTP client is not in the configuration this evidence requires."""


class ResolvedModelMismatchError(CkffClientError):
    """The gateway answered as a different model than the one requested."""


class GatewayProtocolError(CkffClientError):
    """The gateway's response is not a shape this client will interpret."""


class OutputLimitExceededError(CkffClientError):
    """A response exceeded a configured size or token bound."""


class RequestBudgetExceededError(CkffClientError):
    """The run would issue more requests than its plan permits."""


class WallClockExceededError(CkffClientError):
    """The run's total time bound was reached."""


class ConcurrentRequestError(CkffClientError):
    """A second request was started while one was already in flight."""


class SecretMaterialError(CkffClientError):
    """Text about to leave the process, or be written to evidence, looks secret."""


class SequentialRunAborted(CkffClientError):
    """A sequential run stopped early. Carries whatever evidence was collected."""

    def __init__(self, reason: str, result: SequentialRunResult) -> None:
        super().__init__(reason)
        self.reason = reason
        self.result = result


# ---------------------------------------------------------------------------
# Egress hygiene
# ---------------------------------------------------------------------------


def assert_no_secret_material(text: str, *, context: str = "payload") -> None:
    """Raise if ``text`` contains something shaped like a credential."""
    for pattern in SECRET_SHAPED_PATTERNS:
        if pattern.search(text):
            raise SecretMaterialError(
                f"{context} contains material shaped like a credential "
                f"(pattern {pattern.pattern!r}); refusing to continue. The offending "
                "value is deliberately not reproduced in this message."
            )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# HTTP client construction
# ---------------------------------------------------------------------------

#: Transport classes this client accepts. Anything else is refused, because the
#: retry assertion below can only read the shape it knows: an unrecognised
#: transport might retry, and "might" is not a state this evidence can carry.
_PERMITTED_TRANSPORTS: Final[tuple[type, ...]] = (httpx.HTTPTransport, httpx.MockTransport)


def assert_no_client_retry(client: httpx.Client) -> None:
    """Verify, against the object actually constructed, that nothing retries.

    ``httpx`` exposes no public accessor for the connection-retry count, so this
    reads ``httpcore``'s private ``_retries``. That is deliberate. ``httpx`` is not
    pinned in ``pyproject.toml`` — it arrives transitively — so its default could
    change under us, and a keyword argument that a future version renames would
    pass silently. Reading the value back is the only check that stays true. If the
    internal shape is not recognisable, that is an error rather than a pass.

    Redirects are checked here too: a 3xx that ``httpx`` followed would be a second
    request this client never recorded, which is a retry by another name.
    """
    transports: list[Any] = [client._transport, *client._mounts.values()]
    for transport in transports:
        if transport is None:
            continue
        if not isinstance(transport, _PERMITTED_TRANSPORTS):
            raise ClientConfigurationError(
                f"transport {type(transport).__name__} is not one whose retry behaviour "
                "this client can verify"
            )
        if not isinstance(transport, httpx.HTTPTransport):
            continue
        pool = getattr(transport, "_pool", None)
        retries = getattr(pool, "_retries", None)
        if not isinstance(retries, int):
            raise ClientConfigurationError(
                "cannot read the connection-retry count from "
                f"{type(transport).__name__}; the installed httpx/httpcore has an "
                "internal shape this check does not recognise, so zero retries cannot "
                "be evidenced"
            )
        if retries != CLIENT_RETRIES:
            raise ClientConfigurationError(
                f"transport is configured for {retries} connection retries; Task 2B "
                f"requires exactly {CLIENT_RETRIES}. Temporal owns visible retries."
            )
    if client.follow_redirects:
        raise ClientConfigurationError(
            "the client follows redirects; a followed 3xx is an unrecorded second "
            "request and can route to a different upstream"
        )


def build_http_client(
    timeout_seconds: float,
    *,
    transport: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """An ``httpx.Client`` in the only configuration this path accepts.

    ``trust_env=False`` is a fail-closed choice: an ambient ``HTTPS_PROXY`` picked
    up from the environment would put an unrecorded hop between this process and
    the gateway, and the evidence would not say so. A run that genuinely needs a
    proxy should configure it explicitly and record it.
    """
    resolved_transport = transport or httpx.HTTPTransport(retries=CLIENT_RETRIES)
    client = httpx.Client(
        transport=resolved_transport,
        timeout=httpx.Timeout(
            timeout_seconds, connect=min(CONNECT_TIMEOUT_SECONDS, timeout_seconds)
        ),
        follow_redirects=False,
        trust_env=False,
    )
    assert_no_client_retry(client)
    return client


# ---------------------------------------------------------------------------
# Requests and records
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelRequest:
    """One request this run intends to make."""

    alias: str
    prompt_id: str = DEFAULT_PROMPT_ID
    #: ``None`` means "the plan's cap". An explicit value is still capped by it.
    max_completion_tokens: int | None = None
    sequence_index: int = 0


@dataclass(frozen=True)
class CallRecord:
    """One completed call, as evidence.

    Carries no model text. See the module docstring: withholding the content is
    what makes "output cannot steer control flow" a property of the type rather
    than a rule someone has to remember.
    """

    requested_alias: str
    resolved_model: str
    http_status: int
    latency_seconds: float
    prompt_tokens: int
    completion_tokens: int
    content_sha256: str
    content_characters: int
    response_bytes: int
    sequence_index: int = 0
    client_retry_count: int = CLIENT_RETRIES
    gateway_headers: Mapping[str, str] = field(default_factory=dict)

    def as_document(self) -> dict[str, Any]:
        return {
            "requested_alias": self.requested_alias,
            "resolved_model": self.resolved_model,
            "http_status": self.http_status,
            "latency_seconds": round(self.latency_seconds, 4),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "content_sha256": self.content_sha256,
            "content_characters": self.content_characters,
            "response_bytes": self.response_bytes,
            "sequence_index": self.sequence_index,
            "client_retry_count": self.client_retry_count,
            "gateway_headers": dict(self.gateway_headers),
        }


def verify_resolved_model(requested: str, resolved: object) -> str:
    """Byte-for-byte equality, or raise.

    Exact equality and not the ``split("/")[-1]`` normalisation used for the mock
    registry. CKFF aliases are opaque strings the gateway chose, so a
    provider-prefixed echo is a *difference worth failing on* rather than noise to
    be normalised away. This will produce a false alarm if the gateway ever
    reformats what it echoes — that is the intended direction of error, and it is
    recorded in ``docs/task-2b-scaffold.md`` as a known cost.

    A missing, non-string, or empty value is treated as a mismatch. An absent field
    is exactly what a substituting proxy would leave behind.
    """
    if not isinstance(resolved, str) or not resolved.strip():
        raise ResolvedModelMismatchError(
            f"requested {requested!r} but the response carries no usable model "
            f"identifier ({resolved!r}); treating an unknown resolution as a mismatch, "
            "because a run that cannot say which model answered is not evidence"
        )
    if resolved != requested:
        raise ResolvedModelMismatchError(
            f"requested {requested!r} but the gateway resolved {resolved!r}; model "
            "substitution invalidates the evidence and no other model is attempted"
        )
    return resolved


# ---------------------------------------------------------------------------
# The client
# ---------------------------------------------------------------------------


class CkffSequentialClient:
    """One bounded request at a time, with the limits enforced on both sides."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        limits: RunLimits,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = self._validated_base_url(base_url)
        self._credential = self._validated_credential(api_key)
        self.limits = limits
        self._http = http_client or build_http_client(limits.request_timeout_seconds)
        assert_no_client_retry(self._http)
        self.requests_issued = 0
        self._issued_per_alias: dict[str, int] = {}

    # `repr` is where credentials leak into logs and pytest output. Overridden so
    # there is nothing to leak.
    def __repr__(self) -> str:
        return f"CkffSequentialClient(base_url={self.base_url!r})"

    __str__ = __repr__

    @staticmethod
    def _validated_base_url(base_url: object) -> str:
        if not isinstance(base_url, str) or not base_url.strip():
            raise ClientConfigurationError("base URL is empty")
        trimmed = base_url.strip().rstrip("/")
        if not trimmed.startswith("https://"):
            raise ClientConfigurationError("base URL must use HTTPS")
        if "/v1" in trimmed.removeprefix("https://"):
            raise ClientConfigurationError("base URL must not include the /v1 path segment")
        return trimmed

    @staticmethod
    def _validated_credential(api_key: object) -> str:
        # Shape only. The value is never logged, echoed, or written to evidence,
        # and no part of it appears in any exception message raised here.
        if not isinstance(api_key, str) or not api_key.strip():
            raise ClientConfigurationError("no gateway credential was supplied")
        if api_key != api_key.strip():
            raise ClientConfigurationError("gateway credential has surrounding whitespace")
        if len(api_key) < 16:
            raise ClientConfigurationError(
                "gateway credential is shorter than a usable restricted key"
            )
        return api_key

    def issued_for(self, alias: str) -> int:
        return self._issued_per_alias.get(alias, 0)

    # -- before the call --------------------------------------------------

    def prepare_payload(self, request: ModelRequest) -> dict[str, Any]:
        """Build the request body, enforcing every pre-call bound.

        Nothing here touches the network, which is why the budget, token and
        blinding checks can be exercised offline.
        """
        alias = validate_alias(request.alias)
        prompt = get_prompt(request.prompt_id)

        requested_tokens = (
            self.limits.max_completion_tokens
            if request.max_completion_tokens is None
            else request.max_completion_tokens
        )
        if not isinstance(requested_tokens, int) or isinstance(requested_tokens, bool):
            raise OutputLimitExceededError("max_completion_tokens must be an integer")
        if requested_tokens <= 0:
            raise OutputLimitExceededError(
                f"max_completion_tokens must be positive, got {requested_tokens}"
            )
        if requested_tokens > self.limits.max_completion_tokens:
            raise OutputLimitExceededError(
                f"request asks for {requested_tokens} completion tokens, above the "
                f"configured cap of {self.limits.max_completion_tokens}"
            )

        if self.issued_for(alias) >= self.limits.max_requests_per_model:
            raise RequestBudgetExceededError(
                f"{alias!r} has already been asked {self.issued_for(alias)} time(s); the "
                f"per-model budget is {self.limits.max_requests_per_model}"
            )

        for name, text in (("system prompt", prompt.system), ("user prompt", prompt.user)):
            assert_blinded(text, context=name)
            assert_no_secret_material(text, context=name)

        return {
            "model": alias,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "temperature": 0,
            "max_tokens": requested_tokens,
            "stream": False,
        }

    def note_request_issued(self, alias: str) -> None:
        """Count a request the moment it is about to leave, not after it returns.

        Counting on return would let a run that times out repeatedly stay inside
        its budget forever.
        """
        self.requests_issued += 1
        self._issued_per_alias[alias] = self.issued_for(alias) + 1

    # -- after the call ---------------------------------------------------

    def interpret_response(
        self,
        request: ModelRequest,
        *,
        http_status: int,
        headers: Mapping[str, str],
        body: bytes,
        latency_seconds: float,
    ) -> CallRecord:
        """Turn a raw response into a record, refusing anything unexpected.

        Every branch that cannot be understood raises. There is no "best effort"
        reading: a partially understood response would produce a record that looks
        like the others and means something different.
        """
        if http_status != 200:
            raise GatewayProtocolError(
                f"gateway returned HTTP {http_status} for {request.alias!r}; no retry and "
                "no other model is attempted"
            )
        if len(body) > self.limits.max_response_bytes:
            raise OutputLimitExceededError(
                f"response body is {len(body)} bytes, above the cap of "
                f"{self.limits.max_response_bytes}; it is discarded unread rather than "
                "truncated, because a truncated body would hash to something no one can "
                "check"
            )
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise GatewayProtocolError(
                f"response for {request.alias!r} is not decodable JSON: {exc}"
            ) from exc
        if not isinstance(payload, dict):
            raise GatewayProtocolError("response is not a JSON object")

        resolved = verify_resolved_model(request.alias, payload.get("model"))

        choices = payload.get("choices")
        if not isinstance(choices, list) or not choices:
            raise GatewayProtocolError(f"response for {request.alias!r} carries no choices")
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise GatewayProtocolError(
                f"response for {request.alias!r} carries no message content; an empty or "
                "absent completion is an error here, not a zero-length answer"
            )
        if len(content) > self.limits.max_content_characters:
            raise OutputLimitExceededError(
                f"completion is {len(content)} characters, above the cap of "
                f"{self.limits.max_content_characters}"
            )

        usage = payload.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        prompt_tokens = self._non_negative_int(usage.get("prompt_tokens"), "prompt_tokens")
        completion_tokens = self._non_negative_int(
            usage.get("completion_tokens"), "completion_tokens"
        )
        if completion_tokens > self.limits.max_completion_tokens:
            raise OutputLimitExceededError(
                f"gateway reported {completion_tokens} completion tokens, above the "
                f"requested cap of {self.limits.max_completion_tokens}; the cap was not "
                "honoured, so the run stops"
            )

        lowered = {str(k).lower(): str(v) for k, v in dict(headers).items()}
        recorded = {name: lowered[name] for name in RECORDED_RESPONSE_HEADERS if name in lowered}
        for name, value in recorded.items():
            assert_no_secret_material(value, context=f"response header {name}")

        return CallRecord(
            requested_alias=request.alias,
            resolved_model=resolved,
            http_status=http_status,
            latency_seconds=latency_seconds,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            # The only thing kept about the completion itself.
            content_sha256=sha256_text(content),
            content_characters=len(content),
            response_bytes=len(body),
            sequence_index=request.sequence_index,
            gateway_headers=recorded,
        )

    @staticmethod
    def _non_negative_int(value: object, name: str) -> int:
        if value is None:
            return 0
        if isinstance(value, bool) or not isinstance(value, int):
            raise GatewayProtocolError(f"{name} is not an integer: {value!r}")
        if value < 0:
            raise GatewayProtocolError(f"{name} is negative: {value}")
        return value

    # -- the call ---------------------------------------------------------

    def call(self, request: ModelRequest) -> CallRecord:
        """Issue exactly one request. Blocked while Task 2B is blocked.

        The block is checked here, immediately before egress, rather than at
        import or construction time: that keeps every offline part of this module
        testable while leaving no path to the network that skips the guard.
        """
        assert_execution_allowed()
        payload = self.prepare_payload(request)
        self.note_request_issued(request.alias)
        started = time.monotonic()
        response = self._http.post(
            f"{self.base_url}/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self._credential}",
                "Content-Type": "application/json",
                "User-Agent": "eval-lab-task-2b-sequential/1",
            },
            json=payload,
        )
        latency = time.monotonic() - started
        return self.interpret_response(
            request,
            http_status=response.status_code,
            headers=dict(response.headers),
            body=response.content,
            latency_seconds=latency,
        )

    def close(self) -> None:
        self._http.close()


# ---------------------------------------------------------------------------
# The sequential runner
# ---------------------------------------------------------------------------


class _InFlightGuard:
    """Refuses a second request while one is in flight.

    The sequential loop below is already sequential; this exists so that
    "one model at a time" is checkable rather than inferred from reading the
    control flow, and so that a future edit that introduces a thread pool fails
    loudly instead of quietly producing interleaved evidence.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._in_flight = 0
        self.max_observed = 0

    @property
    def in_flight(self) -> int:
        return self._in_flight

    def __enter__(self) -> _InFlightGuard:
        with self._lock:
            if self._in_flight:
                raise ConcurrentRequestError(
                    "a second gateway request was started while one was already in "
                    "flight; Task 2B evaluates exactly one model at a time"
                )
            self._in_flight += 1
            self.max_observed = max(self.max_observed, self._in_flight)
        return self

    def __exit__(self, *exc_info: object) -> None:
        with self._lock:
            self._in_flight -= 1


@dataclass(frozen=True)
class SequentialRunResult:
    """What a run produced, kept strictly separated per model."""

    plan: SequentialRunPlan
    records_by_alias: dict[str, tuple[CallRecord, ...]]
    max_observed_in_flight: int
    elapsed_seconds: float
    aborted_reason: str | None = None

    def evidence_documents(self) -> dict[str, dict[str, Any]]:
        """One document per model, keyed by :func:`alias_slug`.

        Separation is the requirement: one model's evidence must never be blended
        into another's. So each document names exactly one alias, is written to a
        path derived from that alias's slug, and carries no comparison, ranking, or
        aggregate. Whoever wants a comparison builds it from the documents; the
        producer does not hand one over pre-drawn.
        """
        documents: dict[str, dict[str, Any]] = {}
        for alias in self.plan.model_aliases:
            records = self.records_by_alias.get(alias, ())
            document = {
                "document_kind": "task_2b_model_evidence",
                "asserts": (
                    "Nothing about this model's quality. It records what was asked, "
                    "what answered, and under which bounds."
                ),
                "requested_alias": alias,
                "alias_slug": alias_slug(alias),
                "prompt_id": self.plan.prompt_id,
                "limits": self.plan.limits.as_document(),
                "client_retry_count": CLIENT_RETRIES,
                "retry_owner": "temporal",
                "model_substitution_permitted": False,
                "concurrency": 1,
                "calls": [record.as_document() for record in records],
                "call_count": len(records),
            }
            assert_no_secret_material(
                json.dumps(document, sort_keys=True), context=f"evidence for {alias_slug(alias)}"
            )
            documents[alias_slug(alias)] = document
        return documents


class SequentialRunner:
    """Walks the plan's models one at a time, bounded by a total wall clock.

    ``call_fn`` is injected rather than constructed here for two reasons. It keeps
    the sequencing logic testable with no network and no credential, and it means
    the only object that can reach the gateway is the one a caller deliberately
    built — this class has no way to create one.
    """

    def __init__(
        self,
        plan: SequentialRunPlan,
        call_fn: Callable[[ModelRequest], CallRecord],
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.plan = plan
        self._call = call_fn
        self._clock = clock
        self.guard = _InFlightGuard()

    def run(self) -> SequentialRunResult:
        """Execute the plan, or raise :class:`SequentialRunAborted`.

        A run that stops early raises rather than returning a short result. A
        partial run that returns normally is the shape most likely to be treated as
        a whole one by whatever reads it next; the exception carries the partial
        result for anyone who wants to record what was collected.
        """
        started = self._clock()
        records: dict[str, list[CallRecord]] = {alias: [] for alias in self.plan.model_aliases}
        limits = self.plan.limits

        def snapshot(reason: str | None) -> SequentialRunResult:
            return SequentialRunResult(
                plan=self.plan,
                records_by_alias={alias: tuple(values) for alias, values in records.items()},
                max_observed_in_flight=self.guard.max_observed,
                elapsed_seconds=self._clock() - started,
                aborted_reason=reason,
            )

        issued = 0
        # An explicit loop, not a matrix and not a map over an executor. The
        # constraint is meant to be visible in the code that enforces it.
        for alias in self.plan.model_aliases:
            for index in range(limits.max_requests_per_model):
                elapsed = self._clock() - started
                remaining = limits.total_wall_clock_seconds - elapsed
                if remaining <= 0:
                    reason = (
                        f"total wall clock of {limits.total_wall_clock_seconds}s reached "
                        f"before {alias!r} request {index + 1}"
                    )
                    raise SequentialRunAborted(reason, snapshot(reason))
                if remaining < limits.request_timeout_seconds:
                    reason = (
                        f"{remaining:.1f}s remain of the run's wall clock but a request may "
                        f"take {limits.request_timeout_seconds}s; refusing to start one that "
                        "cannot finish inside the bound"
                    )
                    raise SequentialRunAborted(reason, snapshot(reason))
                if issued >= self.plan.total_request_budget:
                    reason = f"request budget of {self.plan.total_request_budget} reached"
                    raise SequentialRunAborted(reason, snapshot(reason))

                request = ModelRequest(
                    alias=alias, prompt_id=self.plan.prompt_id, sequence_index=index
                )
                try:
                    with self.guard:
                        record = self._call(request)
                except CkffClientError as exc:
                    reason = f"{alias!r} request {index + 1}: {exc}"
                    raise SequentialRunAborted(reason, snapshot(reason)) from exc

                issued += 1
                if record.requested_alias != alias:
                    reason = (
                        f"a record for {record.requested_alias!r} was returned while "
                        f"{alias!r} was being evaluated; evidence would be misattributed"
                    )
                    raise SequentialRunAborted(reason, snapshot(reason))
                records[alias].append(record)

        return snapshot(None)


def run_sequential(
    plan: SequentialRunPlan,
    call_fn: Callable[[ModelRequest], CallRecord],
    *,
    clock: Callable[[], float] = time.monotonic,
) -> SequentialRunResult:
    """Convenience wrapper around :class:`SequentialRunner`."""
    return SequentialRunner(plan, call_fn, clock=clock).run()
