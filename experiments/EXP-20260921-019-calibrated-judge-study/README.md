# EXP-20260921-019

This experiment studies how Eval Lab constructs rubric-grounded calibrated
judges and compares independent judge implementations head-to-head.

It reuses the frozen EXP-015 pool and typed System-One packet. The primary
included arms are direct Grok Build, Jev through the Jev-only OpenRouter route,
YOLO-Auto Qwen Flash, and local Qwen 4B. Luna and Sol are excluded under the
vendor-independent orchestrator policy. No OpenCode route is used.

The experiment distinguishes:

- rubric/typed protocol validity;
- label accuracy and cross-judge agreement; and
- calibrated confidence quality when native probabilities are available.

Completed EXP-014 through EXP-017 artifacts are read-only inputs. The report
must never promote a model judgment to objective gold.
