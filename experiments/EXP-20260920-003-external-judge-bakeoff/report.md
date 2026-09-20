# TASK-0007 External Judge and Teacher Bakeoff

Frozen records: 20; identical record IDs claimed: True.

## Provider census

- OpenCode CLI: 1.18.31
- YOLO-Auto /models status: 200; exact qwen3.8-flash present: True
- Required free arms present: {'opencode/nemotron-3.5-lightning-free': True, 'opencode/mimo-v2.5-free': True}

## Results

| Provider/model | OK | Rate limited | Provider error | Parse error | Skipped | Agreement with TASK-0006 local |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| yolo-auto/qwen3.8-flash | 20 | 0 | 0 | 0 | 0 | 8 |
| opencode/nemotron-3.5-lightning-free | 0 | 0 | 1 | 0 | 19 | 0 |
| opencode/mimo-v2.5-free | 0 | 0 | 1 | 0 | 19 | 0 |
| opencode/grok-4.6 | 0 | 0 | 1 | 0 | 19 | 0 |

Provider failures are retained as execution states and excluded from wrong-label metrics. Model outputs are not objective gold.

Luna audit batch: 10 records. Sol hard-disagreement batch: 10 records.

## Limitations

The selected slice is small and public/synthetic. Text-only external responses do not expose calibrated probabilities, so probability metrics are unavailable for those arms. Subscription and provider availability is an execution condition recorded in the artifacts.
