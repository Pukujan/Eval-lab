# CKFF gateway setup for Eval-lab and other projects

## Goal

Use one public HTTPS LiteLLM gateway across multiple backend and agent projects
without sharing the LiteLLM master key, exposing credentials to browsers, or
silently switching models.

Gateway base URL:

```text
https://litellm-production-8656.up.railway.app
```

The base URL is public configuration. Keys are secrets.

## Trust boundary

```text
project backend / CI / cloud agent
        |
        | project-specific virtual key
        v
CKFF LiteLLM gateway
        |
        | upstream credentials held only by CKFF
        v
configured model provider
```

The `LITELLM_MASTER_KEY` stays only in the Railway LiteLLM service. It must never
be placed in a project repository, GitHub Actions secret for a public repository,
frontend build, agent prompt, or chat message.

## One key per project and environment

Create a separate restricted virtual key for each consumer. Examples:

- `eval-lab-task-2b`
- `claude-code-cloud`
- `hades-v2-development`
- `hades-v2-production`
- `scc-v2-development`

Each key should have:

- a model allowlist;
- a small explicit budget;
- an expiration or rotation plan;
- a unique alias identifying the project and environment;
- no permission to generate or revoke other keys.

Do not reuse one virtual key across all applications. A leak in one application
must not give access to every application or consume every budget.

## Standard backend environment contract

Use these names for normal OpenAI-compatible applications:

```env
OPENAI_BASE_URL=https://litellm-production-8656.up.railway.app/v1
OPENAI_API_KEY=REDACTED_PROJECT_VIRTUAL_KEY
OPENAI_MODEL=gpt-5.6-luna
```

The exact model name must be an alias returned by CKFF. Do not guess model names.

For application code that uses neutral names, prefer:

```env
AI_GATEWAY_BASE_URL=https://litellm-production-8656.up.railway.app/v1
AI_GATEWAY_API_KEY=REDACTED_PROJECT_VIRTUAL_KEY
AI_MODEL=gpt-5.6-luna
```

Map these neutral values into the SDK at process start.

## Claude Code environments

Where the Claude Code runtime permits environment variables, configure:

```env
ANTHROPIC_BASE_URL=https://litellm-production-8656.up.railway.app
ANTHROPIC_AUTH_TOKEN=REDACTED_CLAUDE_CODE_VIRTUAL_KEY
ANTHROPIC_MODEL=gpt-5.6-luna
ANTHROPIC_SMALL_FAST_MODEL=gemini-3.5-flash
```

This configures that Claude Code runtime. It does not change claude.ai chat
sessions that do not expose runtime environment settings.

## Frontend rule

Never put a CKFF key in browser or mobile application code, including variables
with public prefixes such as `NEXT_PUBLIC_`, `VITE_`, or `EXPO_PUBLIC_`.

The frontend calls its own backend. The backend holds the restricted CKFF key and
calls the gateway.

## GitHub Actions

For each repository that needs gateway access:

1. Add repository secret `CKFF_API_KEY` containing that repository's restricted
   virtual key.
2. Add repository variable `CKFF_BASE_URL` with the public gateway URL.
3. Keep the model name in workflow input or a non-secret repository variable.

**In this repository, `CKFF_BASE_URL` must be the evaluation service:**

```text
https://litellm-eval-production.up.railway.app
```

The connectivity workflow has no default and refuses to run if the variable is
missing or set to anything else. That is deliberate: a fallback pointing at the
production gateway would produce a *green* connectivity check against a service
whose retries, pooled routes, cooldowns and parameter-dropping make its latency
and failure numbers unattributable. The dangerous failure mode there is that it
appears to work.

This repository includes a manual workflow named **CKFF connectivity**. It makes
one bounded request, performs no client retry, **follows no redirect**, and
prints only metadata and a hash of the returned content. Refusing redirects
matters because urllib would otherwise copy the `Authorization` header to the
redirect target — across origins and onto plain `http` — so a redirect is a
credential-disclosure path, not a routing detail.

Other repositories can call the reusable composite action after this change is
merged. Pin it to the exact merge commit:

```yaml
permissions:
  contents: read

steps:
  - uses: Pukujan/Eval-lab/.github/actions/ckff-smoke@REPLACE_WITH_FULL_COMMIT_SHA
    with:
      base-url: ${{ vars.CKFF_BASE_URL }}
      api-key: ${{ secrets.CKFF_API_KEY }}
      model: gpt-5.6-luna
```

## Eval-lab rules

Eval-lab needs stronger controls than ordinary applications:

- begin with one model alias: `gpt-5.6-luna`;
- use a dedicated `eval-lab-task-2b` virtual key;
- allow only that model on the first key;
- disable cross-model fallback;
- use zero hidden proxy retries for the Eval-lab alias;
- let Temporal own visible retries;
- keep the private verifier inaccessible to the implementation agent;
- let Inspect own the restricted patch workspace;
- record requested model, resolved model, usage, latency, request identifier, and
  gateway configuration identity in evidence.

The current CKFF statement of five same-model retries is acceptable for ordinary
application availability, but not for an evidence-driven Eval-lab run. A separate
zero-retry model alias or gateway route is required before Task 2B evidence can be
accepted.

## Rollout policy

Do not add CKFF to archived repositories or frontend-only repositories. Roll out
only to active backends and agents that actually make model calls. For each
project:

1. identify whether the model call belongs in a backend, worker, CI job, or cloud
   agent;
2. mint a dedicated virtual key;
3. add the key to that platform's encrypted secret store;
4. add the public base URL and model alias as non-secret configuration;
5. run one smoke request;
6. verify spend and model resolution in CKFF;
7. only then enable application traffic.

## Rotation and incident response

Rotate a project key without rotating every project. Revoke only the affected
key, replace it in that project's secret store, redeploy, and verify one smoke
request. Rotate the master key separately if it was exposed or accessible to an
untrusted agent.
