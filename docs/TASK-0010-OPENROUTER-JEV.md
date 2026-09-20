# TASK-0010 OpenRouter Jev Integration

Verified 2026-09-20:

- pinned model: `typesafe/jev-1.13`
- rolling alias: `~typesafe/jev-latest`
- Jev 1.13 context: 32K
- OpenRouter price observed at planning: $0.042/M input, output free
- OpenRouter Decisions endpoint: `https://openrouter.ai/api/alpha/decisions`

The rolling alias is a canary, never the scientific pinned arm.

Eval Lab owns the typed question semantics; provider adapters translate the repository spec to wire formats.

Credential:

`OPENROUTER_API_KEY`

Never print/commit credentials.

Use `typesafe-ai/system-one-adapter-python` as a differential reference/adapter when it cleanly supports YOLO-Auto. Keep the repository-owned spec independent from the library.

`browser-use/jev-ultrafast` is an architectural reference for later typed action routing, not a TASK-0010 dependency.
