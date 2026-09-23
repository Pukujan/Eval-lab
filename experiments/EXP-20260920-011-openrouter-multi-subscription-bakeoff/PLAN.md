# EXP-20260920-011 OpenRouter multi-subscription bakeoff

Status: plan-only at creation. This is an append-only follow-up to the provider-path diagnosis for TASK-0010. The OpenCode Zen and OpenCode Go paths are not used: Zen returned HTTP 402 for insufficient account funds, Go returned HTTP 403 requiring an active Go subscription, and the local LiteLLM path was unavailable.

## Frozen inputs

- Benchmark: `EvalLab-Select v0.1.0`
- Benchmark fingerprint: `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`
- ARC revision: `210d026faf9955653af8916fad021475a3f00453`
- Canonicalization: `eval-lab-select-single-v1`
- Provider records: deterministic first 500 records in the frozen `final_evaluation` partition
- Student: frozen TASK-0009 TF-IDF + logistic-regression arm D; no retraining
- Typed System-One: `eval-lab-system-one` v0.1.0; single labels `pass`/`fail`, pairwise labels `A`/`B`/`TIE`, context cap 4096
- Confidence and target error definitions: inherited from TASK-0010/EXP-009; provider labels do not select thresholds or prompts

## Provider arms

- `grok`: OpenRouter `x-ai/grok-4.6`
- `luna`: OpenRouter `openai/gpt-5.6-luna`
- `sol`: OpenRouter `openai/gpt-5.6-sol`

Every request uses the OpenAI-compatible streaming endpoint with one frozen record per request, temperature 0, thinking disabled where accepted, and normalized typed output. The OpenRouter key is loaded only from the ignored local `.env`; it is never printed or committed. Provider failures and parse failures remain explicit and never fall back across arms.

## Outputs and acceptance

The runner writes one normalized JSONL file per arm, results, provider status, a matched differential matrix, a report, and checksums. A bounded smoke must pass before the 500-record run. The 500-record run is accepted only when record IDs and model identities are complete, outputs validate, and low-error coverage includes binomial uncertainty. This experiment is reported separately from pinned/rolling Jev and from the Qwen streaming retry artifact.

Exact planned commands are recorded in the TASK-0010 checkpoint after execution.
