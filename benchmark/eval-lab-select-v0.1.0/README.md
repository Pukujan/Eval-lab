# EvalLab-Select v0.1.0

Status: frozen release.

EvalLab-Select is a compact objective benchmark for calibrated rubric judging, selective escalation, and typed decision-model differential evaluation.

Fingerprint: `18a440b4f0a82e09a9ab234815ed0f095c7fbe64a82879fd8a31206eb83ed7e5`.

The release contains 2,863 threshold-selection records from 1,427 source families and 2,356 final-evaluation records from 1,176 source families. Source families are disjoint across the two partitions; records are canonical variants and are not duplicated or resampled.

ARC-Challenge is pinned to revision `210d026faf9955653af8916fad021475a3f00453`. The synthetic source families used by TASK-0009 training are excluded from this release's threshold pool; only non-training synthetic splits are included.

Rebuild and verify from the repository root:

```powershell
$env:PYTHONPATH = "$PWD\src"
.venv\Scripts\python.exe scripts/build_selective_benchmark.py
.venv\Scripts\python.exe scripts/validate_research_artifacts.py --benchmark benchmark/eval-lab-select-v0.1.0
```

The release includes deterministic source manifests/rebuild instructions, split definitions, checksums, RO-Crate metadata, PROV-O lineage, SHACL shapes, and a benchmark card covering intended use, limitations, and licensing.

It is not intended to claim universal human-evaluation coverage.
