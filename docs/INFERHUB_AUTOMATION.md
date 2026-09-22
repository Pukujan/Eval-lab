# InferHub automation guide

This guide records the safe Eval Lab integration for the InferHub account in
`D:\\claude\\inferhub`. It uses the OpenAI-compatible inference surface and
keeps the account token on the Windows host. Never copy the token into a
prompt, source file, benchmark artifact, or commit.

## What is live

At the 2026-09-22 live check, the authenticated `GET /v1/models` endpoint
returned `251` model rows. The local InferHub snapshot immediately before the
check contained `247`, so four provider-qualified IDs were newly surfaced in
the live catalog:

| ID | Minimum input ask | Minimum output ask |
| --- | ---: | ---: |
| `cp/cline-pass/deepseek-v4-pro` | 0.099 | 0.297 |
| `cp/cline-pass/kimi-k3` | 0.45 | 2.25 |
| `cp/cline-pass/mimo-v2.5-pro` | 0.261 | 0.522 |
| `cp/cline-pass/qwen3.7-plus` | 0.3 | 1.2 |

The four rows are newly surfaced in the live catalog, not proof of their
release dates. The API's `created` field is the catalog observation timestamp,
not a reliable upstream release timestamp. I checked upstream release notes
before choosing benchmark arms. The release evidence is:

- Gemini 3.8 Flash: 2026-09-02, Google's newest Flash release at the time of
  the check ([Google announcement](https://blog.google/innovation-and-ai/models-and-research/gemini-models/3-8-flash-and-3-8-flash-cyber/)).
- Claude Fable 5.1/Mythos 5.1: 2026-09-01, Anthropic's newest listed model
  release ([Anthropic newsroom](https://www.anthropic.com/news)).
- DeepSeek V4.1 Flash: 2026-09-10, the latest V4 Flash release, with native
  multimodal support ([DeepSeek release notes](https://api-docs.deepseek.com/updates/)).
- Qwen3.8 Omni Flash: 2026-09-20, the newest Qwen route in this catalog
  ([Alibaba announcement](https://www.alibabacloud.com/blog/qwen3-8-omni-flash-omni-senses--agentic-delivery-_603580)).
- GLM-5.3-Flash: 2026-09-22, the newest GLM Flash release
  ([Z.AI release post](https://autoclaw.z.ai/blog/model/glm-5.3-flash/)).
- Hy4 Preview: 2026-08-28, Tencent's latest Hy4 release
  ([Tencent release](https://www.tencent.com/tencent-releases-and-open-sources-tencent-hy4-preview/)).
- Muse Spark 1.3: 2026-09-02, Meta's latest Muse Spark release
  ([Meta Research announcement](https://research.meta.ai/blog/introducing-muse-spark-1-3)).
- Qwen3.8 Max: 2026-08-03, Alibaba's flagship release used where a rail
  lacks the newer Omni route ([Alibaba announcement](https://www.alibabacloud.com/en/press-room/alibaba-unveils-qwen3-8-max?_p_lc=1)).

The resulting rule is one cheapest live route and one latest-release live route
per active non-ChatGPT InferHub rail. If the same route satisfies both, it is
run once. Prices below are the live minimum asks in USDC per one million
tokens:

| Rail | Cheapest route | Latest route |
| --- | ---: | --- |
| `ag` | `ag/gemini-3.8-flash-high` — 0.00075 / 0.00375 | same route |
| `cc` | `cc/claude-haiku-4-5` — 0.10 / 0.50 | `cc/claude-fable-5-1` — 0.97 / 4.85 |
| `cp` | `cp/zai/glm-5.3-flash` — 0.0072 / 0.024 | `cp/cline-pass/qwen3.8-max` — 0.28 / 0.84 |
| `cb` | `cb/deepseek-v4.1-flash` — 0.00015 / 0.0006 | `cb/hy4-preview` — 0.02085 / 0.062525 |
| `cbcn` | `cbcn/deepseek-v4.1-flash` — 0.00225 / 0.009 | `cbcn/hy4-preview` — 0.01668 / 0.05002 |
| `cmc` | `cmc/meta/muse-spark-1.3-contributor` — 0.0047 / 0.0094 | same route |
| `ocg` | `ocg/mimo-v2.5` — 0.07 / 0.14 | `ocg/qwen3.8-max` — 1 / 3 |
| `ali` | `ali/qwen3.8-omni-flash` — 0.00015 / 0.00047 | same route |
| `zai` | `zai/glm-5.3-flash` — 0.00015 / 0.0005 | same route |

Values are USDC per one million tokens and are the lowest observed asks, not a
guaranteed transaction price. InferHub can route to a higher available ask
when the cheapest provider is at its concurrency limit. Use a provider-
qualified ID when the route matters; bare aliases intentionally enable
cheapest-first routing and are not appropriate for a fixed-arm benchmark.

The Xiaomi `mimo` rail reported zero active providers in the snapshot, so it is
not runnable in this wave even though its latest model is `mimo-v2.5-pro`.
ChatGPT/Codex IDs (`gpt-*`, `cx/*`) are deliberately excluded from this
InferHub arm set. Qwen Flash remains allowed; the separate local Qwen4B arm is
still excluded from the current wave.

## Configuration

The handoff repository already contains the token in its ignored `.env`:

```text
INFERHUB_API_KEY=...
INFERHUB_API_URL=https://api.inferhub.dev/v1
INFERHUB_MANAGEMENT_URL=https://inferhub.dev/api
```

For Eval Lab, pass the handoff `.env` explicitly:

```powershell
$env:PYTHONPATH = 'src'
$env:INFERHUB_API_URL = 'https://api.inferhub.dev/v1'
```

The benchmark runner reads `INFERHUB_API_KEY` from the supplied `--env-file`.
It never prints the key and writes only non-secret provider metadata.

## Read-only discovery

Use the authenticated models endpoint to refresh the live list. This consumes
inference rate-limit budget but does not create a model request:

```powershell
$env:PYTHONPATH = 'src'
python scripts/check_inferhub_catalog.py `
  --env-file D:\\claude\\inferhub\\.env
```

The account's management endpoints are read-only for discovery and usage
inspection. They have a separate 30-requests-per-minute account limit. The
inference surface is documented as 500 requests per minute by default and
returns `X-RateLimit-*` headers.

## One streaming request

InferHub's OpenAI-compatible chat endpoint is
`https://api.inferhub.dev/v1/chat/completions`. Streaming uses OpenAI SSE;
the final usage chunk may include the charged `usage.cost` value.

```python
import os
from openai import OpenAI

client = OpenAI(
    base_url=os.environ["INFERHUB_API_URL"],
    api_key=os.environ["INFERHUB_API_KEY"],
)

stream = client.chat.completions.create(
    model="zai/glm-5.3-flash",
    messages=[{"role": "user", "content": "Return exactly {\\\"label\\\":\\\"pass\\\"}."}],
    max_tokens=32,
    temperature=0,
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content if chunk.choices else None
    if delta:
        print(delta, end="")
```

The Eval Lab runner uses the same SSE route, collects the streamed content,
records the surfaced model and usage when present, and checkpoints one
canonical prediction at a time. It does not send gold labels to the provider.

## Eval Lab execution

The new append-only experiment is `EXP-20260922-023-inferhub-wave`. Its runner
accepts one exact model per process so several model arms can run concurrently
without mixing artifacts:

```powershell
$env:PYTHONPATH = 'src'
python scripts/run_inferhub_arm.py `
  --pool experiments/EXP-20260921-015-grok-luna-qwen-bakeoff `
  --experiment-id EXP-20260922-023-inferhub-wave `
  --partition public_selection `
  --model zai/glm-5.3-flash `
  --workers 4 `
  --timeout 120 `
  --env-file D:\\claude\\inferhub\\.env `
  --output experiments/EXP-20260922-023-inferhub-wave/runs/public-zai-glm-53-flash-20260922
```

Run the one-record canary first in a new output directory. Only after every
selected route returns a usable canary should the public and then blind
partitions be started. Use `--resume` only on the same run directory; never
overwrite a completed run. Rate limits, provider errors, timeouts, and parse
errors remain explicit unresolved statuses and receive no fallback label.

The first safe concurrency is four workers per model, with at most eight model
processes at once. This stays below the documented account request ceiling
while allowing the independent model arms to make progress concurrently.

## Sources and route boundary

- InferHub handoff: `D:\\claude\\inferhub\\AGENT-QUICKSTART.md`
- OpenAPI snapshot: `D:\\claude\\inferhub\\docs\\openapi.json`
- Live model discovery: `GET https://api.inferhub.dev/v1/models`
- OpenAI-compatible inference: `https://api.inferhub.dev/v1`
- Read-only management surface: `https://inferhub.dev/api`

InferHub is a separate API route from direct Grok Build CLI, direct Codex,
YOLO-Auto, and OpenRouter Jev. A surfaced InferHub model ID must not be
reported as evidence about a direct upstream route.
