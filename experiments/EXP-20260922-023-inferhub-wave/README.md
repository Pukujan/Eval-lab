# EXP-20260922-023 — InferHub cheapest/latest rail wave

This append-only experiment evaluates the cheapest live route and the latest
officially verifiable release available on each active non-ChatGPT InferHub
rail. It uses the immutable EXP-015 source pool and does not modify EXP-022,
the direct Grok/Jev/Qwen wave.

The selection is route-qualified. InferHub marketplace rails are not treated
as model creators; release dates are verified against the upstream model
owner's official announcement or release notes. The live catalog snapshot and
release evidence are retained in this directory.

The Xiaomi MiMo rail is excluded from execution because the catalog reported
zero active providers. The model remains documented as an availability
finding, not as a failed benchmark arm.

Provider failures, rate limits, timeouts, and parse failures remain explicit
unresolved execution states. They are never converted into labels or silently
re-routed to another model.
