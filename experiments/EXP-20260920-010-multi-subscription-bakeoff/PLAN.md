# EXP-20260920-010 — Multi-subscription judge bakeoff

Status: preregistered plan, frozen before any new provider evaluation.

This experiment is a separate follow-up to the provider-blocked TASK-0010 arm. It does not alter, relabel, or overwrite `EXP-20260920-009-selective-escalation`. Its purpose is to use the currently available subscription-backed OpenCode models while YOLO-Auto Qwen is unavailable.

## Frozen inputs

- Benchmark: `EvalLab-Select v0.1.0`.
- Benchmark fingerprint: `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`.
- Threshold-selection partition: `2,863` records from `1,427` source families.
- Final-evaluation partition: `2,356` records from `1,176` disjoint source families.
- Provider evaluation pool: the deterministic first `500` final-evaluation records in committed record order, identical for every arm. Provider labels never select records, thresholds, prompts, or models.
- Source revision: `allenai/ai2_arc` revision `210d026faf9955653af8916fad021475a3f00453`, plus the committed synthetic objective sources.
- Canonicalization: `eval-lab-select-single-v1`.
- Primary student: frozen TASK-0009 TF-IDF plus logistic-regression arm D, restored from its committed artifact; no retraining.
- Typed protocol: `eval-lab-system-one` v0.1.0; context cap `4096`; legal single labels `pass` and `fail`; pairwise labels remain `A`, `B`, and `TIE`.
- Confidence and threshold artifacts are inherited for descriptive comparison only: maximum calibrated class probability, top-two margin as secondary measure, targets `0.01`, `0.02`, `0.05`, and `0.10`.

## Provider arms

The following arms are evaluated independently through the OpenCode CLI with their surfaced model IDs recorded exactly:

| Arm | Provider/model | Access | Planned status |
|---|---|---|---|
| grok | `opencode/grok-4.6` | OpenCode/SuperGrok subscription | evaluate |
| luna | `opencode/gpt-5.6-luna` | OpenCode/ChatGPT subscription | evaluate |
| sol | `opencode/gpt-5.6-sol` | OpenCode/ChatGPT subscription | evaluate |

Deferred arms are recorded but are not substituted into this run:

- `yolo-auto/qwen3.8-flash`: deferred because the TASK-0010 provider block returned transport/provider errors and stalled bulk calls. It remains the original TASK-0010 arm for a later retry.
- Local Qwen 1.7B and 4B: deferred because no local weights are present in the standard Hugging Face cache. Downloading weights and measuring hardware feasibility requires a separately recorded setup step.

The existing TASK-0010 pinned `typesafe/jev-1.13` and rolling `~typesafe/jev-latest` outputs remain reference arms in EXP-009. They are not pooled with one another or silently replaced by this bakeoff.

## Evaluation rules

Each available arm receives the same canonical typed question and the same 500 record IDs. The runner preserves one normalized prediction per record with model identity, execution status, latency, surfaced usage where available, and a secret-free error type. Provider failures remain unresolved and never receive a local fallback label.

The report will provide per-arm status counts, resolved accuracy/risk, Wilson 95% intervals, resolved and execution coverage, latency summaries, cost/usage fields when the provider exposes them, and agreement matrices against the frozen student and separately against the two Jev reference arms. Probability metrics are unavailable unless an arm returns a validated probability map. No arm is treated as objective gold; benchmark answer keys remain the gold source.

The experiment will not use provider outputs for threshold selection, arm selection, prompt selection, or record selection. The matched random control and selective-routing summaries remain the EXP-009 artifacts; this experiment adds a same-record subscription comparison and a separate System-One differential matrix.

## Planned artifacts

Under this directory:

- `PLAN.md` and `experiment.yaml`;
- one normalized JSONL file per evaluated arm;
- `results.json` with exact model IDs, status counts, coverage, uncertainty, latency, and usage;
- `differential.json` with same-record pairwise agreements and missingness;
- `provider-status.json` for deferred or unavailable arms;
- `report.md`, checksums, and a machine-readable run manifest.

No API key, raw credential-bearing environment, or unbounded raw provider transcript may enter the repository.

## Exact planned commands

After the runner and offline tests are committed:

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv\Scripts\python.exe scripts/run_multi_subscription_bakeoff.py `
  --benchmark benchmark/eval-lab-select-v0.1.0 `
  --output experiments/EXP-20260920-010-multi-subscription-bakeoff `
  --limit 500 `
  --timeout 60 `
  --env-file .env
.venv\Scripts\python.exe scripts/validate_multi_subscription_bakeoff.py `
  --experiment experiments/EXP-20260920-010-multi-subscription-bakeoff
```

The local repository contract, Ruff, full pytest suite, and artifact validation must pass before and after provider execution. A provider outage produces an explicit blocked arm and does not change the frozen protocol.

## Acceptance boundary

This bakeoff is complete when every available subscription arm has been attempted on the matched 500-record pool or its external failure is explicitly recorded, all outputs validate, and the report is reproducible. It does not claim TASK-0010’s missing Qwen arm is complete and does not authorize TASK-0002.
