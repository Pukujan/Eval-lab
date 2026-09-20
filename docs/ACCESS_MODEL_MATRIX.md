# Access and Model Matrix

## Operating rule

Existing subscription-covered access should be actively utilized when relevant and technically available. Do not silently replace an existing subscription path with a separately metered API path.

## Jev

Primary model:
- provider: OpenCode Zen
- model id: `jev-1.13-free`
- role: specialized classification judge
- TASK-0003 must request this exact id by default
- never silently fall back to paid `jev-1.13`

## Qwen3.8 Flash through YOLO-Auto

This is the user's authoritative Qwen3.8 Flash automation path.

- provider: YOLO-Auto
- API: OpenAI-compatible
- base URL: `https://yolo-auto.com/v1`
- model id: `qwen3.8-flash`
- local credential variable: `YOLO_AUTO_API_KEY`
- access status: user reports it is already configured locally
- roles: external judge, bulk rubric/critique teacher, hard-negative generator, dataset auditor

Rules:
- TASK-0007 verifies model access before a full run.
- Use `qwen3.8-flash`, not a generic routing alias.
- Do not substitute Alibaba or OpenCode Zen Qwen endpoints unless a later task explicitly changes provider.
- Preserve provider/model metadata in every artifact.
- Subscription throttling is execution metadata, not model error.

## SuperGrok subscription

Preferred automation path:
- SuperGrok subscription through supported xAI/OpenCode OAuth integration
- discover and record the exact surfaced model id

Roles:
- hard-case judge
- adversarial critic
- failure-cluster analyst
- hard-negative generator

Rules:
- actively use the subscription in TASK-0007 and TASK-0008 when available;
- do not assume a particular Grok version without checking;
- do not silently route to a separately metered API endpoint.

## ChatGPT Luna and Sol

Access:
- ChatGPT subscription surface

Luna roles:
- execution agent
- batch audit
- rubric review
- error clustering
- teacher critique

Sol roles:
- difficult disagreement review
- research-design audit
- adversarial/rubric analysis

Rules:
- use both subscriptions actively for high-value review;
- do not model ChatGPT subscription access as an OpenAI API;
- use reproducible batch import/export metadata;
- outputs are teacher/audit metadata, not objective gold.

## OpenCode Zen free general models

TASK-0007 enumerates current free models at run time.

Preferred arms when available:
- `nemotron-3.5-lightning-free`
- `mimo-v2.5-free`

Optional arms when available:
- `nemotron-3-ultra-free`
- `ling-3.0-flash-fin-free`
- `muse-spark-1.3-contributor-free`

Optional anonymous control:
- `big-pickle`

Use only public/synthetic Eval Lab records with free-trial providers unless project data policy changes.

## Local models

TASK-0006 ladder:
1. `Qwen/Qwen3-0.6B`
2. `Qwen/Qwen3-1.7B` if feasible
3. `Qwen/Qwen3-4B` optional

TASK-0009 chooses the student from measured evidence.

## Access priority

1. objective verifier/answer key for truth;
2. already-configured subscription/free automated access;
3. local models;
4. ChatGPT/SuperGrok subscription workflows for high-information cases;
5. separately metered APIs only under a future explicit experiment.

No retry/fallback path may silently change this ordering.
