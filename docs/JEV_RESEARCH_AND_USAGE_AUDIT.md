# Jev Research and Usage Audit

**Snapshot date:** 2026-09-21  
**Scope:** TypeSafe Jev/System One semantics, the Jev-only OpenRouter route
authorized for Eval Lab, and real open-source integrations.

## Executive findings

Jev is not a smaller chat model that should be prompted to emit a JSON answer.
It is a typed decision service: the caller supplies a state and a closed set of
questions, and Jev returns typed answers plus probability information where the
question type supports it. The application remains responsible for control
flow, deterministic checks, side effects, thresholds, and escalation.

The recurring pattern in the strongest real integrations is:

1. Convert the environment into a compact, structured observation.
2. Ask one narrow `choice`, `noul`, or `score` question per judgment.
3. Make all legal options explicit and mutually exclusive.
4. Validate the answer, the option membership, and the probability map.
5. Let ordinary code execute, retry, verify, or escalate.

This is directly relevant to Eval Lab. A judge prompt should not ask Jev to
write an explanation, count, perform arithmetic, or invent a schema. For our
objective records, a single `Choice` over `pass/fail` or `A/B/TIE` is the right
primitive. The gold label remains the benchmark verifier or answer key; Jev's
answer is always a prediction.

## Official contract audited

### State and questions

TypeSafe documents `state` as a string, JSON object, or array of text values.
Each request evaluates one state against one or more typed questions. Questions
in the same request are independent and see the same state.

The three primitives are:

| Primitive | Use | Native answer |
|---|---|---|
| `choice` | one option from a known unordered set | `choice`, full `probabilities`, `confidence` |
| `score` | one ordered level on a rubric | `score`, `legend`, full `probabilities`, `confidence` |
| `noul` | a clean yes/no statement | `noul`, the probability of yes |

`Choice` is the appropriate primitive for Eval Lab's forced labels. `Noul` is
not a replacement for a binary `Choice` when we need a named `pass`/`fail`
label and a legal probability map. `Score` is appropriate only when the levels
are ordered and their meaning is explicitly defined.

### Confidence is not correctness

TypeSafe describes `confidence` as a statistic derived from the answer's
probability distribution. It is not a proof, an objective label, or a guarantee
that an individual prediction is correct. Eval Lab must therefore retain the
native distribution and measure calibration against held-out objective gold.
For `noul`, the returned number is the probability of yes and there is no
separate confidence field.

### Question design

The official guidance is consistent with the open-source implementations:

- keep the question atomic and literal;
- put the evidence in `state` and the judgment in `instructions`;
- describe every option in `criteria`;
- add an `other`/`none` option when the set is not exhaustive;
- ask independent questions together and combine them in code;
- keep deterministic rules and side effects outside Jev;
- use conservative, risk-specific thresholds and validate them on local data.

### OpenRouter route used by this repository

The authorized Jev route is the OpenRouter Decisions API, not Chat
Completions:

```text
POST https://openrouter.ai/api/alpha/decisions
model: typesafe/jev-1.13        # pinned arm
model: ~typesafe/jev-latest     # separate rolling canary
```

The request has `model`, `state`, and a `questions` map. The response has an
`answers` map and may include the resolved model, usage, request/provider
metadata, probabilities, and confidence. The API is an alpha decision route;
we must preserve the exact model requested and record the surfaced model when
the provider returns it.

The Jev route is the only OpenRouter use authorized for the current Eval Lab
program. Grok remains direct xAI Build CLI; Luna remains direct Codex Luna;
OpenCode is not an authorized route for any new experiment. The historical
TASK-0003 OpenCode adapter and its evidence are retained as history and are not
used by current experiments.

Jev is a completed structured decision response, not a text stream. The
inspected official and community Jev integrations use an ordinary JSON POST;
streaming is not part of the TypeSafe decision contract audited here. Eval Lab
should not add `stream=true` to Jev calls or treat a streamed text fragment as
a decision. Parallelism should come from independent requests or question
fan-out, with checkpointing and provider-status accounting.

## Open-source usage audit

Star counts are a GitHub snapshot observed on 2026-09-21, not a quality
measurement. Jev launched recently, so even the largest Jev-specific projects
are young. The code patterns below were inspected directly rather than inferred
from project names.

| Project | Snapshot stars | What the code actually does | Relevance to Eval Lab |
|---|---:|---|---|
| [browser-use/jev-ultrafast](https://github.com/browser-use/jev-ultrafast) | 16.0k | Builds a dynamic action space, asks one `Choice` for the operation and several compatible target `Choice`s, validates every returned probability and selected ID, and executes only a fresh observed DOM action. A separate small text model writes field values. | Strong evidence for explicit action spaces, freshness checks, fail-closed normalization, and keeping text generation separate from Jev decisions. Do not copy its OpenRouter text-helper route into Eval Lab. |
| [awlevin/typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use) | 746 | Converts deterministic OCR/accessibility state into one request containing multiple `Choice`s; Jev picks actions, while deterministic code clicks and a separate writer handles free text. It stops on low confidence, no-op repetition, or a step budget. | Supports compact structured state, multiple questions per request, confidence gates, and code-owned execution. |
| [wy-coliney/jev-browser-use](https://github.com/wy-coliney/jev-browser-use) | 322 | Uses Jev for navigation, clicks, toggles, and scrolling while retaining a stronger agent for typing, visual judgment, and final verification. | Supports a split between cheap closed decisions and high-level reasoning, plus explicit verification after `DONE`. |
| [jkudish/jev-browser](https://github.com/jkudish/jev-browser) | 227 | Maps current DOM elements to bounded action IDs, asks Jev to choose an action, checks `done` and `goal_achieved` independently, and treats malformed/out-of-list answers as review states. Jev never generates text. | Strong example of ID-based action spaces, bounded loops, and abstention/escalation rather than trusting a label blindly. |
| [supercorp-ai/supercov](https://github.com/supercorp-ai/supercov) | 91 | Asks Jev repeated yes/no questions about code-quality properties, performs arithmetic and aggregation locally, and caches answers by content. | Supports atomic criterion questions, deterministic aggregation, and reproducible caching. It does not make Jev the source of code-coverage gold. |
| [TypeSafeAI/typesafe-router](https://github.com/TypeSafeAI/typesafe-router) | reference implementation | Official example sends one `Choice` question, reads the selected option and per-option probabilities, and keeps the API key server-side. | Confirms the native wire shape and the correct normalization boundary. |

### Concrete code patterns observed

The most useful implementation details were:

- `browser-use/jev-ultrafast/jev_ultrafast/model.py` builds `criteria` from
  actual observed IDs, sends several questions in one request, rejects an
  answer whose choice is not in the current option set, and checks that the
  probability keys and mass are valid.
- `awlevin/typesafe-computer-use` explicitly says that the state must be
  reduced to deterministic OCR/accessibility observations; its action loop
  does not let model output become a selector or arbitrary code.
- `jkudish/jev-browser` normalizes each named answer from
  `body.answers[question_id]`, treats a missing or malformed answer as
  `needsReview`, and uses the returned confidence only as a routing signal.
- `TypeSafeAI/typesafe-router/lib/jevClient.ts` documents the native
  `POST /v1/systemone` shape and preserves the full option probability map.
- `supercov` asks one property at a time and does the score arithmetic itself,
  which is the correct separation between model judgment and deterministic
  measurement.

## Eval Lab implications

### What was already right

- The active benchmark uses the Jev-only OpenRouter Decisions route.
- The pinned and rolling model IDs are separate arms.
- The frozen record pool and typed packet are immutable for EXP-014 through
  EXP-019.
- `Choice` is used for the closed `pass/fail` and `A/B/TIE` spaces.
- Provider failures remain execution states rather than fabricated labels.
- The active runner records the surfaced provider model and usage metadata when
  they are present.

### Corrections made in TASK-0024

1. The active typed-spec builder no longer imports the historical
   `eval_lab.jev` module, which carried the old OpenCode route. This makes the
   current provider path structurally independent of OpenCode while preserving
   historical TASK-0003 files unchanged.
2. Eval Lab now sends descriptive criteria for `pass`, `fail`, `A`, `B`, and
   `TIE`, instead of sending the label as its own description. This follows the
   official question contract and reduces ambiguity for the decision model.
3. Response normalization now descends into
   `answers.<question_id>`/answer envelopes and preserves native probability
   maps and confidence when they are returned. The previous shallow traversal
   could keep the label while silently dropping a nested probability map.
4. A regression test covers the native nested answer shape.

These are adapter corrections only. No completed experiment artifact was
rewritten and no live provider call was made by TASK-0024.

### Still intentionally separate

The current adapter sends one record per request. The official guidance and
the inspected projects show that several independent questions can be put in
one request, and OpenRouter's Jev Lab example also batches multiple records by
placing their IDs in one shared state and question map. A future batch-runner
task may measure that optimization, but it must use a new experiment ID and
must not change the frozen EXP-014–EXP-019 results.

## Evidence limits

- TypeSafe's calibration claims are vendor documentation until Eval Lab measures
  them against independent objective gold.
- GitHub stars, demos, and self-reported speedups are ecosystem evidence, not
  benchmark evidence.
- The open-source projects mostly use Jev for routing, browser actions,
  moderation, or code-quality triage. That demonstrates the intended software
  pattern but does not establish accuracy on Eval Lab's objective judge pool.
- Jev cannot replace deterministic verifiers, executable tests, or answer keys.

## Sources

Primary documentation:

- [System One](https://docs.typesafe.ai/concepts/system-one)
- [State](https://docs.typesafe.ai/concepts/state)
- [Primitives](https://docs.typesafe.ai/primitives)
- [API reference](https://docs.typesafe.ai/api)
- [Confidence](https://docs.typesafe.ai/confidence)
- [How to build with TypeSafe](https://docs.typesafe.ai/concepts/how-to-build-with-system-one)
- [OpenRouter Jev model page](https://openrouter.ai/typesafe/jev-1.13)
- [OpenRouter Jev Lab example](https://openrouter.ai/labs/jev/compile)

Code inspected:

- [browser-use/jev-ultrafast model.py](https://raw.githubusercontent.com/browser-use/jev-ultrafast/main/jev_ultrafast/model.py)
- [browser-use/jev-ultrafast agent.py](https://raw.githubusercontent.com/browser-use/jev-ultrafast/main/jev_ultrafast/agent.py)
- [TypeSafeAI/typesafe-router Jev client](https://raw.githubusercontent.com/TypeSafeAI/typesafe-router/main/lib/jevClient.ts)
- [jkudish/jev-browser](https://github.com/jkudish/jev-browser)
- [awlevin/typesafe-computer-use](https://github.com/awlevin/typesafe-computer-use)
- [wy-coliney/jev-browser-use](https://github.com/wy-coliney/jev-browser-use)
- [supercorp-ai/supercov](https://github.com/supercorp-ai/supercov)
