# EXP-20260921-017 — Local Qwen 4B judge calibration

Status: completed. The exact EXP-015 pool is unchanged; model outputs are not gold.

## Primary blind holdout

| View | Accuracy | Brier | NLL | ECE | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| raw | 0.44605263157894737 | 0.7036824847148387 | 1.076729516647522 | 0.3411375292308107 | 1.0 |
| calibrated | 0.44605263157894737 | 0.5160339956496602 | 0.7430236501814631 | 0.07834063916107518 | 1.0 |

Calibration temperature was fit separately by judgment mode on public_selection only.

## Reference arms

| Arm | Route | Accuracy | Coverage | Status |
| --- | --- | ---: | ---: | --- |
| grok | direct_grok_build_cli_subscription | 0.43783068783068785 | 0.9947368421052631 | {'ok': 756, 'provider_error': 4} |
| luna | direct_codex_chatgpt_subscription | 0.9842105263157894 | 1.0 | {'ok': 760} |
| qwen_flash | yolo_auto_openai_compatible | 0.9909502262443439 | 0.5815789473684211 | {'ok': 442, 'provider_error': 1, 'rate_limited': 317} |
| jev_pinned | openrouter-jev-only | 0.9 | 1.0 | {'ok': 760} |

The direct Grok/Luna/Qwen Flash references come from EXP-015; pinned Jev comes from the separate Jev-only EXP-018 OpenRouter run. OpenRouter is not used for Grok, Luna, Sol, or Qwen, and OpenCode is not used.

## Runtime and limitations

- Model: `Qwen/Qwen3-4B` at revision `1cfa9a7208912126459214e8b04321603b3df60c`.
- Runtime: `4bit`, `torch.float16`, `cuda:0`; context cap `2048`.
- The frozen pool's maximum measured input prompt was 755 tokens, so the 2,048-token cap did not truncate this pool.
- Provider failures remain explicit in reference status counts and are not counted as ordinary wrong answers.
