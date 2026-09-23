# Benchmark Expansion Roadmap

Status: planning roadmap recorded 2026-09-21. This document authorizes no
provider calls and no benchmark execution by itself.

## Purpose

The current Eval Lab result is a calibration-focused study of lightweight judges
using frozen, objective-oriented records. The next phase should test whether the
same calibration and rubric-construction methods hold on harder, independently
verifiable benchmark families.

The benchmark families below are deliberately separate experiments. They must
not be pooled into a single leaderboard number because they differ in task
type, environment, answer format, verifier strength, and contamination risk.

## Current baseline and routing policy

EXP-014 through EXP-019 are immutable. The new phase begins from the completed
TASK-0019 state and creates a new experiment directory for every changed
dataset, rubric, prompt, model, seed, calibration method, or evaluation
protocol.

Provider routing remains explicit:

- Grok is allowed only through the direct authenticated xAI `grok` Build CLI.
- OpenCode is not used for any arm.
- OpenRouter is allowed only for the Jev arm when Jev is explicitly in scope.
- Luna and Sol are Codex-subscription routes only when a future experiment
  explicitly includes them; they are not silently substituted for another arm.
- Local Qwen and Jev remain separate, reproducible judge/reference resources.

Streaming, surfaced model IDs, command versions, and route status may be
recorded in execution metadata, but a route failure is not a benchmark answer
and must not be silently converted into a score.

## Inspect AI integration boundary

Inspect AI was not rejected as inadequate. It is useful as a task/solver/scorer,
sandbox, logging, and execution-harness layer. Eval Lab remains the canonical
research layer because it owns the parts that matter for this study:

- preregistration and immutable experiment identity;
- canonical records, source-family splits, and fingerprints;
- per-record gold-label provenance;
- typed judge packets and calibration-only fitting;
- deterministic perturbations and adversarial controls;
- provider routing and failure metadata;
- accuracy, balanced accuracy, macro F1, Brier, NLL, ECE, consistency,
  risk/coverage, latency, and cost reports;
- checksums, rebuild instructions, and manuscript-facing artifacts.

The intended boundary is therefore:

```text
Eval Lab manifest / gold policy / split / calibration / report
                         |
             optional Inspect AI adapter
                         |
       task solver, sandbox, scorer, or environment
```

An Inspect AI implementation may be used where it gives a reliable harness,
but its default model graders are not objective gold. Any scorer imported from
Inspect must be wrapped by the Eval Lab adapter contract and tested against the
declared gold provenance.

## Candidate tracks and order

| Priority | Track | Primary objective signal | Main verifier or scorer | Why it belongs | Main caution |
|---|---|---|---|---|---|
| 1 | HumanEval | executable code correctness | unit-test pass/fail | compact, reproducible, strong objective signal | sandbox and security controls |
| 2 | ARC-AGI-1/2 | exact structured grid transformation | exact grid match plus task metadata | tests compositional generalization and structured outputs | dataset revision and answer representation must be frozen |
| 3 | LegalBench objective subset | rule application, classification, extraction | exact answer key or deterministic normalized match | adds legal reasoning without making the whole suite subjective | choose only tasks with explicit gold and clear labels |
| 4 | FinanceBench objective subset | numeric answer and evidence retrieval | numeric tolerance, normalized answer, citation/evidence checks | tests quantitative and evidence-grounded reasoning | open explanations need a separate adjudication track |
| 5 | SWE-bench / DeepSWE | repository-level code repair | patch application plus repository tests | tests long-horizon agentic software work | expensive, environment-heavy, contamination-sensitive |
| 6 | OSWorld | computer-use task completion | VM snapshot/state checks and task-specific assertions | tests grounded interaction rather than text-only judgment | requires isolated VMs, GUI state, and replayable setup |
| 7 | Humanity's Last Exam | expert/multimodal knowledge | audited answer key where available; adjudication otherwise | useful stress test after the objective tracks | many items are not fully deterministic and require careful gold audit |

The recommended first implementation is HumanEval. It gives the lab a clear
end-to-end adapter pattern: a frozen prompt, a generated answer, a sandboxed
execution verifier, and an explicit correctness label. ARC-AGI is the next
recommended track because it exercises structured outputs without requiring a
full interactive environment.

## Objective-strength taxonomy

Every record must declare the strongest available label provenance rather than
being described generically as “objective.”

### Tier A: deterministic execution or state verification

Examples include HumanEval, repository repair tasks in SWE-bench/DeepSWE, ARC
exact-grid matching, and OSWorld state assertions. These can provide a strong
binary or structured result when the environment and verifier are frozen.

### Tier B: benchmark answer key

Examples include selected ARC items, selected LegalBench tasks, numeric FinanceBench
items, and answer-key subsets of Humanity's Last Exam. The key itself still needs
source, revision, and audit metadata; an answer key is provenance, not a claim
that every item is unambiguous.

### Tier C: adjudicated or judge-dependent evaluation

Open-ended legal explanations, free-form financial evidence explanations, and
many HLE items belong here unless a deterministic key is established. These are
valid future studies, but they must be reported separately from deterministic
accuracy and must never be mixed into objective gold without an adjudication
protocol.

## Required adapter contract

Before a benchmark is run, its adapter must provide:

1. dataset name, revision/commit, license/access terms, and source URL;
2. canonical JSONL records retaining the source problem ID;
3. task type and typed input/output contract;
4. per-record gold provenance using the categories in
   `docs/EXPERIMENT_PROTOCOL.md`;
5. deterministic split rules, source-family isolation, and dataset fingerprint;
6. verifier/scorer code with unit tests and explicit normalization/tolerance;
7. environment/runtime image or setup instructions when execution is required;
8. separate calibration, development, and final evaluation partitions;
9. explicit handling for abstention, malformed output, timeout, and execution
   failure;
10. provider/model/route metadata that cannot be confused with answer labels;
11. rebuild instructions and checksums for every published artifact;
12. contamination and benchmark-leakage notes where the source permits them.

For judge-model studies, the adapter must additionally define what the judge is
asked to predict: exact correctness, rubric dimensions, severity, pairwise
preference, or confidence. A judge's confidence is an evaluated output, not
gold merely because the judge supplied it.

## Experiment gates

Each future track follows the same gates:

1. **Feasibility gate:** verify access/licensing, objective-strength tier,
   environment requirements, and an implementable scorer.
2. **Adapter gate:** build a small mocked runner and scorer tests before any
   provider labels; verify schema, fingerprints, and failure handling.
3. **Preregistration gate:** freeze dataset revision, sample, prompt/rubric,
   model arms, seeds, calibration split, and metrics.
4. **Execution gate:** run smoke tests, preserve exact surfaced model IDs and
   route metadata, then run the frozen pool into separate output files.
5. **Audit gate:** compute answer metrics, calibration metrics, agreement and
   consistency, inspect verifier failures, and publish checksums/rebuild steps.
6. **Paper gate:** add a track to the paper only after its report is complete;
   keep deterministic and adjudicated tracks visibly separated.

## Proposed implementation sequence

1. HumanEval adapter and objective judge packet.
2. ARC-AGI exact-grid adapter and structured-output judge packet.
3. LegalBench objective subset with task-level gold audit.
4. FinanceBench numeric/evidence subset with separate free-form track only if
   adjudication is available.
5. SWE-bench or DeepSWE after sandbox capacity and runtime budget are confirmed.
6. OSWorld after VM snapshot/state-verifier infrastructure is ready.
7. Humanity's Last Exam after the lab has an explicit answer-key/adjudication
   policy for expert and multimodal items.

Each item above becomes a new task and a new experiment; no completed experiment
is overwritten.

## Non-goals for this roadmap

- no provider execution;
- no benchmark downloads or hidden test material committed to the repository;
- no OpenCode route;
- no OpenRouter route for Grok, Luna, Sol, or Qwen;
- no automatic replacement of Eval Lab artifacts with Inspect AI logs;
- no single blended score across unrelated benchmark families;
- no claim that a model judge is objective gold without declared provenance.

## Reference entry points

These are starting points for future adapter tasks, not approvals to download or
run them in TASK-0020:

- Inspect AI: https://inspect.aisi.org.uk/
- HumanEval: https://github.com/openai/human-eval
- ARC: https://github.com/fchollet/ARC-AGI
- LegalBench: https://github.com/HazyResearch/legalbench
- FinanceBench: https://github.com/czyssrs/FinQA
- SWE-bench: https://github.com/SWE-bench/SWE-bench
- DeepSWE: https://github.com/agentica-project/DeepSWE
- OSWorld: https://github.com/xlang-ai/OSWorld
- Humanity's Last Exam: https://github.com/centerforaisafety/hle
