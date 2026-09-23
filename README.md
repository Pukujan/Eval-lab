# Eval Lab

<p align="center">
  <img src="assets/eval-lab-banner.png" alt="Eval Lab — Build AI judges you can trust" width="100%">
</p>

> An agent can produce a convincing answer before you have time to read it. Eval Lab is about making the next question measurable: **when should we trust the judgment, and when should we ask for help?**

Eval Lab is a **reproducible research lab for lightweight AI judges**. It compares their decisions with **objective evidence**, checks whether their confidence means anything, and studies when an uncertain case should move to a **stronger judge or a person**.

The goal is *not* to make a model sound more certain. The goal is to make evaluation **more honest, more affordable, and easier to audit**.

## The short version

People can generate AI output **very quickly**. Checking that output is still **slow**.

Ask an agent to grade a hundred answers and it will return a hundred neat verdicts. Some will be right. Some will be **confidently wrong**. Some will change when two candidates swap places. A human reviewer can catch the difficult cases, but sending every case to a strong model or a person is **expensive**.

Eval Lab explores a **practical middle path**:

1. **Start with labels we can defend.**
2. **Give every judge the same evidence.**
3. **Measure accuracy, consistency, confidence, latency, and cost.**
4. **Let a small judge handle routine cases.**
5. **Send uncertain cases onward** instead of pretending they are easy.

That is the product idea and the research question in one sentence: **make routine judgments cheap, make uncertainty visible, and keep a trace of why a decision was made.**

## Why this exists

The hard part of agentic software is no longer **producing an answer**. It is deciding whether the answer is **good enough to use**.

The problem gets sharper when the output is **plausible**. A broken JSON object is easy to reject. A polished explanation with one wrong assumption is not. A judge can also fail in less obvious ways:

- it can agree with confident-sounding nonsense;
- it can reward style instead of correctness;
- it can be biased by the order of two candidate answers;
- it can say “high confidence” without being right more often;
- it can be too expensive to run on every record;
- it can fail at the provider layer, leaving no valid decision at all.

<p align="center">
  <img src="assets/eval-lab-problem.png" alt="A researcher and robot sort through conflicting AI outputs with different confidence signals" width="100%">
</p>

Eval Lab treats those as **measurement problems**. It does not assume that a larger or more articulate model is automatically a better judge. It asks what the system can demonstrate on records whose labels come from an **answer key, deterministic verifier, executable test, or documented human adjudication**.

## What Eval Lab is

Eval Lab is a **measurement harness, experiment record, and set of research contracts**. It is *not* a chatbot wrapper and it is *not* a leaderboard that turns one model’s opinion into truth.

The lab gives multiple judges the **same canonical record**, collects normalized predictions, and evaluates them against a **declared source of truth**. This makes it possible to compare:

- a structured decision judge such as Jev;
- a small local model such as Qwen3-0.6B;
- a compact classifier or other lightweight baseline;
- a stronger judge used only for escalation or analysis.

Jev is interesting here because it is evaluated as a **structured decision and routing component**, not merely as a chat model. It is *one judge under test*. It is never silently promoted to ground truth.

### The four ideas underneath the project

<table>
  <tr>
    <td><img src="assets/icons/objective-truth.svg" alt="" width="52"></td>
    <td><strong>Objective first</strong><br>Prefer an executable verifier or answer key over a model’s explanation of what the answer should be.</td>
  </tr>
  <tr>
    <td><img src="assets/icons/calibrated-confidence.svg" alt="" width="52"></td>
    <td><strong>Confidence should earn its name</strong><br>A probability is useful only when it lines up with what happens in held-out data.</td>
  </tr>
  <tr>
    <td><img src="assets/icons/selective-routing.svg" alt="" width="52"></td>
    <td><strong>Uncertainty should change the route</strong><br>Easy cases can stay local; ambiguous cases can move to Jev, a stronger judge, or a human.</td>
  </tr>
  <tr>
    <td><img src="assets/icons/reproducible-evidence.svg" alt="" width="52"></td>
    <td><strong>Leave an evidence trail</strong><br>Every result should point back to its source revision, split policy, model identity, and experiment configuration.</td>
  </tr>
</table>

## How the system works

The technical story is deliberately **simple to follow**, even though the implementation is careful.

<p align="center">
  <img src="assets/eval-lab-system-square.png" alt="A calm square illustration of a researcher and robot reviewing a three-step decision path" width="520">
</p>

### 1. Start with a question we can check

Public or synthetic source data enters through a **dataset adapter**. The adapter preserves source IDs, split information, prompt text, answer-key material, and licensing or revision metadata.

When possible, the gold label comes from a **deterministic verifier or trusted answer key**. A strong model can help explain a failure or propose a hard example, but that explanation is stored separately from gold provenance.

### 2. Give every judge the same record

The repository turns source material into a canonical `JudgeRecord`. It contains the task, rubric, candidate answer or pair of candidates, split, perturbation metadata, and gold label.

The **same record goes to each judge**. A provider does not get extra evidence just because its context window is larger. That keeps comparisons meaningful.

### 3. Keep predictions comparable

Every adapter returns a normalized `JudgePrediction` with the **record ID, judge identity, protocol version, label, probabilities or raw scores**, execution status, latency, token usage, and provider metadata.

A provider failure is **not quietly turned into a wrong answer**. The system records whether a request was successful, rate-limited, malformed, skipped, or otherwise unavailable.

### 4. Measure the decision, not just the headline accuracy

Eval Lab tracks **accuracy and balanced accuracy**, but it also looks at:

- Brier score, negative log likelihood, and expected calibration error;
- position-swap and rubric-paraphrase consistency;
- risk/coverage and the error rate among locally accepted cases;
- latency, token usage, and cost per 1,000 decisions;
- provider failures and unresolved records;
- aggregate and per-domain behavior.

### 5. Route uncertainty instead of hiding it

The selective-escalation direction asks one operational question: **can a calibrated local judge identify the cases it should not own?**

The intended pattern is:

```text
local judge + calibrated confidence
              |
       confident enough?
          /          \
        yes           no
         |             |
   accept locally   escalate to Jev,
                   stronger review, or a person
```

The threshold is chosen from **development or calibration data**. Final evaluation stays frozen. If the escalation provider fails, the record remains **unresolved**; it does not magically become a local success.

## The technical contract

### Canonical records

The core data path follows the system design in [`docs/SDD.md`](docs/SDD.md):

```text
source data
    ↓
dataset adapter → SourceRecord
    ↓
verifier / answer key → GoldLabel
    ↓
candidate construction → JudgeRecord
    ↓
Jev / local judge / other adapter → JudgePrediction
    ↓
metrics / calibration / perturbation analysis
    ↓
experiment artifact and report
```

The important boundary is between `GoldLabel` and `JudgePrediction`: **a judge predicts; it does not get to write its own answer key.**

### Split discipline

The default split vocabulary is `train`, `dev`, `calibration`, and `test`.

**Variants derived from one source problem inherit the same split.** Calibration parameters and routing thresholds are fitted before final evaluation. **Test labels are not used to tune prompts, rubrics, thresholds, providers, or calibration parameters.**

### Gold provenance

The schema distinguishes:

- `deterministic_verifier`;
- `answer_key`;
- `executable_test`;
- `human_adjudication`;
- `weak_model_supervision`.

The first four can be treated as trusted according to the experiment policy. **Weak model supervision is never silently presented as objective gold.**

### Execution status

Prediction labels and provider execution state are separate. The current contract includes states such as:

`ok` · `rate_limited` · `provider_error` · `parse_error` · `skipped`

That distinction matters. **“The judge said FAIL”** and **“the judge never returned a valid decision”** are different research findings.

### Context and protocols

The first system targets realistic low-resource hardware with a shared context envelope of 4,096 tokens or less. Jev supports direct typed decisions and criterion-level atomic questions; repository code owns any documented aggregation rule.

The first public benchmark focus is ARC-Challenge, alongside deterministic and synthetic fixtures covering arithmetic, multiple-choice reasoning, machine-checkable instruction following, structured output, and simple code/output verification.

<p align="center">
  <img src="assets/eval-lab-evidence-portrait.png" alt="A portrait-oriented illustration of a researcher checking answer evidence and confidence calibration" width="360">
</p>

## What is implemented, and what is still a question

This project is intentionally honest about the difference between infrastructure and evidence.

| Area | Current state |
| --- | --- |
| Canonical schema and deterministic fixtures | Implemented and tested |
| Jev adapter and normalized provider statuses | Implemented; live availability depends on provider quota |
| Metrics, calibration, perturbation checks, and selective-risk utilities | Implemented as the measurement foundation |
| ARC-Challenge adapter and source fingerprinting | Implemented for the first public benchmark path |
| Lightweight local judge baseline | Implemented and evaluated on the committed slices |
| Hard-negative generation and compact training pilot | Recorded as append-only experiment artifacts |
| Selective escalation to a stronger judge | Active research direction; do not read it as a finished benchmark claim |

The repository does *not* claim that a small judge has solved general evaluation. It is building the instruments needed to find out **where a small judge is useful, where it fails, and whether routing makes the overall system safer and cheaper**.

## Repository map

| Path | What belongs there |
| --- | --- |
| [`src/eval_lab/`](src/eval_lab/) | Schemas, datasets, judges, calibration, metrics, and reporting code |
| [`scripts/`](scripts/) | Reproducible runners, source adapters, and validation entry points |
| [`tests/`](tests/) | Deterministic unit and contract tests |
| [`experiments/`](experiments/) | Immutable manifests, predictions, metrics, and reports for completed runs |
| [`docs/PDD.md`](docs/PDD.md) | Product and research intent |
| [`docs/SDD.md`](docs/SDD.md) | System architecture and data contracts |
| [`docs/TDD.md`](docs/TDD.md) | Testing strategy |
| [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md) | Rules for preregistration, splits, and evidence |
| [`checkpoints/CURRENT.md`](checkpoints/CURRENT.md) | The latest durable handoff state |
| [`tasks/`](tasks/) | One scoped task, branch, and checkpoint per unit of work |

## Start here

If you are a person, start with [`PROJECT.md`](PROJECT.md), then read [`docs/PDD.md`](docs/PDD.md) for the why and [`docs/SDD.md`](docs/SDD.md) for the how.

If you are an agent, also read [`AGENTS.md`](AGENTS.md), [`checkpoints/CURRENT.md`](checkpoints/CURRENT.md), and the active task file before editing anything. **Git is project memory:** important state belongs in task logs and checkpoints, not only in a conversation.

For the reusable writing and visual-generation recipe behind this README, see [`docs/README_CONTENT_VISUAL_SYSTEM.md`](docs/README_CONTENT_VISUAL_SYSTEM.md) and [`assets/README-ASSET-MANIFEST.yaml`](assets/README-ASSET-MANIFEST.yaml).

## Run the local gate

The **core contract and tests do not require paid provider access**.

```bash
python -m venv .venv
# activate the environment
python -m pip install --upgrade pip
pip install -e "[dev]"

python scripts/check_repo_contract.py
ruff check .
pytest -q
```

For an optional Jev smoke test, configure the required local credential and run:

```bash
python scripts/jev_smoke.py
```

Keep credentials in local environment variables or ignored `.env` files. **Never commit keys, tokens, private benchmark material, model weights, or caches.**

## Research rules we will not quietly bend

- **A model judgment is not objective gold** just because the model is strong.
- **A test label is not a tuning signal.**
- **A rate limit is not a wrong prediction.**
- **A confidence score is not calibration evidence by itself.**
- **A benchmark number is not portable** without its source revision, split policy, and code version.
- **A completed experiment is append-only;** changed prompts, datasets, seeds, or calibration methods get a new experiment ID.
- **A good README should explain the limits of the claim** as clearly as the ambition behind it.

## Frequently asked questions

### Is this another chatbot project?

**No.** The objects of study are judge systems and their decisions. Chat models can help design rubrics, analyze failures, or create adversarial cases, but the measurement layer keeps those roles separate from gold labels.

### Does Eval Lab claim that Jev is always better?

**No.** Jev is one structured decision judge in the comparison. The point is to measure its behavior against objective evidence and against lightweight local alternatives.

### Does a small local judge replace human review?

**Not by default.** The selective-routing question is whether it can safely handle a declared portion of routine cases while making uncertainty visible. Ambiguous domains and high-stakes decisions still need stronger review and human judgment.

### Why measure calibration?

Because a judge that **knows when it is likely to be wrong** can be more useful operationally than a judge with a similar average accuracy but no reliable sense of uncertainty.

## Content and visual contract

This README follows the pinned [`content-generation-modules` v0.1.2](https://github.com/Pukujan/content-generation-modules/releases/tag/v0.1.2) adapter in [`.content-system/`](.content-system/). **Narrative raster images carry a short title and subtitle** so each visual can introduce one idea without replacing the explanation; SVG research icons remain text-free. The responsive review and prompt record are in [`docs/content-system-preview.md`](docs/content-system-preview.md) and [`docs/content-system-preview.html`](docs/content-system-preview.html).

## Contributing

Please read [`AGENTS.md`](AGENTS.md) and [`docs/HANDOFF_PROTOCOL.md`](docs/HANDOFF_PROTOCOL.md) before starting work. Use **one task file, one branch, and one worktree**. Record the exact files changed, commands run, validation results, decisions, unresolved questions, and next atomic action before handing work off.

The project is early on purpose. A careful negative result, a reproducible provider failure, or a smaller-than-expected safe coverage number is still useful evidence.
