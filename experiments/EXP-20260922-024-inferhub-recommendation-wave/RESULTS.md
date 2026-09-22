# EXP-20260922-024 results

The recommendation-policy wave completed on the immutable EXP-015 pool. The
operational nine-family shortlist was deduplicated to the cheapest exact route
per family. Eight routes passed canary and completed both partitions. MiMo V2.5
was retained as an unavailable arm because `cp/cline-pass/mimo-v2.5` returned
HTTP 402 on both canary attempts; no alternate provider route was substituted.

## Blind holdout — primary result

Accuracy is conditional on resolved labeled records. Coverage is the resolved
fraction of all 760 blind records. Parse and provider failures remain outside
accuracy and are listed explicitly.

| Family | Route | Resolved | Coverage | Accuracy | Statuses |
|---|---|---:|---:|---:|---|
| Qwen3.8 Flash | `ali/qwen3.8-flash` | 760/760 | 1.0000 | 0.9921 | 760 ok |
| Qwen 3.8 Max | `ali/qwen3.8-max` | 760/760 | 1.0000 | 0.9908 | 760 ok |
| GLM 5.2 | `ali/glm-5.2` | 727/760 | 0.9566 | 0.9917 | 33 parse_error |
| Kimi K2.7 Code | `ali/kimi-k2.7-code` | 758/760 | 0.9974 | 0.9855 | 758 ok, 1 parse_error, 1 provider_error |
| DeepSeek V4 Flash | `cbcn/deepseek-v4-flash` | 611/760 | 0.8039 | 0.9984 | 149 parse_error |
| DeepSeek V4.1 Flash | `cb/deepseek-v4.1-flash` | 621/760 | 0.8171 | 0.9871 | 139 parse_error |
| GLM 5.3 Flash | `cbcn/glm-5.3-flash` | 756/760 | 0.9947 | 0.9788 | 756 ok, 2 parse_error, 2 provider_error |
| MiniMax M3 | `cbcn/minimax-m3` | 744/760 | 0.9789 | 0.9798 | 744 ok, 16 parse_error |

The full offline comparison, including balanced accuracy, macro-F1, latency,
and same-record agreement, is in `runs/blind-comparison-20260922/`. Public
selection is in `runs/public-comparison-20260922/`.

## Interpretation

Qwen3.8 Flash is the best operational default in this run because it combines
full blind coverage with the highest full-coverage accuracy. DeepSeek V4 Flash
has the highest conditional accuracy but is not the safest default because
nearly one in five blind records was unresolved by the current visible-content
parser. These results do not promote any model judgment to gold; frozen answer
keys and deterministic verifiers were used offline only.
