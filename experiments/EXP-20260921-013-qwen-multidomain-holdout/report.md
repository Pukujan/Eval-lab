# EXP-20260921-013 — Qwen multidomain holdout

Provider: `yolo-auto`; model: `qwen3.8-flash`; transport: one frozen record per streaming request.

The public-selection and blind-holdout partitions were frozen before provider execution. Gold labels were used only after provider execution for objective scoring. Provider failures remain unresolved and no fallback labels were fabricated.

Pool fingerprint: `b7edd61269f0f7757e734bc7e3f665ac2bcd6d908a1e56f73f0b0291d55b64d8`; blind record-ID fingerprint: `409428fc71b447d0114dd7a1929cbed34269a4318ef249c108582b70069d8d61`.

| Dataset | Public n/resolved | Public accuracy | Blind n/resolved | Blind accuracy | Blind unresolved | Blind p95 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `allenai/ai2_arc:ARC-Easy` | 160/158 | 0.9747 | 100/100 | 0.9700 | 0.0000 | 991.6947 |
| `cais/mmlu:abstract_algebra` | 20/20 | 0.9000 | 40/40 | 0.9000 | 0.0000 | 878.8353 |
| `cais/mmlu:computer_security` | 20/20 | 0.9000 | 40/40 | 0.8250 | 0.0000 | 999.2819 |
| `cais/mmlu:elementary_mathematics` | 20/20 | 0.8500 | 40/40 | 0.9000 | 0.0000 | 1067.2525 |
| `cais/mmlu:high_school_biology` | 20/20 | 0.9000 | 40/40 | 1.0000 | 0.0000 | 769.6903 |
| `cais/mmlu:high_school_world_history` | 20/20 | 1.0000 | 40/40 | 0.9750 | 0.0000 | 1037.4576 |
| `cais/mmlu:logical_fallacies` | 20/20 | 1.0000 | 40/38 | 0.8684 | 0.0500 | 801.3024 |
| `cais/mmlu:machine_learning` | 20/19 | 0.6316 | 40/39 | 0.7949 | 0.0250 | 1007.4978 |
| `cais/mmlu:professional_law` | 20/20 | 0.8500 | 40/38 | 0.8421 | 0.0500 | 1001.1066 |
| `eval-lab-select-v0.1.0` | 120/120 | 0.9750 | 120/120 | 0.9917 | 0.0000 | 796.8542 |
| `eval-lab-synthetic:arithmetic` | 12/11 | 1.0000 | 5/5 | 0.6000 | 0.0000 | 1126.6262 |
| `eval-lab-synthetic:code` | 12/11 | 0.8182 | 5/5 | 1.0000 | 0.0000 | 454.1285 |
| `eval-lab-synthetic:multiple` | 12/12 | 0.4167 | 5/4 | 0.2500 | 0.2000 | 4113.8983 |
| `eval-lab-synthetic:structured` | 12/12 | 0.5833 | 5/5 | 0.2000 | 0.0000 | 593.3304 |
| `openai/gsm8k:main` | 160/156 | 0.6795 | 200/200 | 0.6550 | 0.0000 | 1048.7486 |

Public selection: `549/639` correct among resolved records; unresolved rate `0.0139`.
Blind holdout: `637/754` correct among resolved records; unresolved rate `0.0079`.

Calibration metrics requiring probabilities/logprobs are unavailable for this Qwen route. This experiment evaluates label accuracy and operational reliability; it does not claim calibrated Qwen confidence.

See `limitations.md` for threats to validity and `qwen-public-report-20260921/report.md` and `qwen-blind-report-20260921/report.md` for full per-partition metrics and Wilson intervals.
