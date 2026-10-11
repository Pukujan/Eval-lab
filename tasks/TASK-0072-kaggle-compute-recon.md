# TASK-0072 — Kaggle GPU compute path: machine-shape recon and the Strata memlock blocker

## Status

Active — tracked by GitHub issue #105. Branch `task/TASK-0072-kaggle-compute-recon`.
Reconnaissance only; no eval run yet, no AGENTS.md compute exception requested.
Precedent: TASK-0065 (issue #83), the free-tier Colab T4 path.

## Objective

Establish whether the owner's Kaggle account is a usable eval compute path for
the large MoE judge arms that do not fit the canonical machine, and record the
measured session shape so a future task can drive it without re-probing.

The concrete question the owner asked: can Kaggle run Qwen3.8-Flash-Next (the
125B-class MoE) or the dense Qwen3.8-27B GSQ-RCO, and is a second T4 worth it.

## Goal

Record, from real batch-kernel runs rather than documentation, whether the
owner's Kaggle account is a usable eval compute path for the large MoE judge
arms that do not fit the canonical machine — and name the one thing that would
block the MoE engine if it is not liftable.

## Scope

- Probe the account's real accelerator, RAM, disk, CPU, and pinned-memory
  limits with batch (script) kernels.
- Record the measured T4 session shape, the accelerator lineup that is actually
  offered, and the quota behaviour.
- Test whether `root` + `CAP_SYS_RESOURCE` can lift `RLIMIT_MEMLOCK` in-container,
  which is the single blocker for the Strata MoE engine.
- Write `docs/compute/kaggle.md` as the source of truth for this path.

Out of scope: running a scored experiment, creating an `experiments/` directory,
modifying AGENTS.md, cloning the repository to a Kaggle VM, or committing any
token or credential.

## Gold and safety rules

- No gold label, token, or credential is uploaded, committed, or printed. The
  Kaggle token lives only in the owner's Desktop config `.env` and is read into
  a shell variable per call.
- Only gold-free request files may ever be served on this path; scoring stays
  offline in the canonical `.venv`, exactly as the TASK-0065 Colab exception
  requires. Any future eval use follows that exception's shape.
- The repository is never cloned or copied to a Kaggle VM.
- No completed experiment artifact is modified.
- Scratch kernels and scripts live outside `D:\development`, at `C:\work\kgprobe-*`
  and `C:\work\kgstrata*`.

## Acceptance

1. The accelerator actually offered to this account is identified, with the
   distinguishing diagnostic (silent CPU downgrade vs `QUEUED`) recorded.
2. The T4 session shape is measured, not assumed: VRAM per card, cgroup RAM cap,
   vCPU count, CPU flags, writable disk and its speed, and `RLIMIT_MEMLOCK`.
3. The memlock question is answered green or red: can the cap be lifted
   in-container, or not.
4. `docs/compute/kaggle.md` exists and states the lineup, the quota, the
   self-termination property of batch kernels, and the recording rule.
5. Findings are durable in the repository, not only in memory or chat.

## Acceptance criteria

The Objective, Scope, Gold and safety rules, and Acceptance sections above are
the acceptance criteria for this task.

## Files in scope

- `tasks/TASK-0072-kaggle-compute-recon.md`
- `docs/compute/kaggle.md` (new)
- `checkpoints/CURRENT.md`

## Checkpoint log

### 2026-10-11 — issue filed; recon complete except the memlock verdict

Status: issue #105 filed; task file written; branch created. `docs/compute/kaggle.md`
written. The memlock probe is still QUEUED on Kaggle, so criterion 3 is open;
criteria 1, 2, 4, 5 are met.

The owner's direct complaint that prompted this checkpoint: work was only going
to memory, not the repository. This task file is the correction — the last
commit before this branch was `f544a93` (2026-10-06, a sibling session).

Measured facts (all from batch kernels, not documentation):

- **Accelerator offered: `NvidiaTeslaT4` only.** With `machine_shape:
  NvidiaTeslaT4` the run sits in `KernelWorkerStatus.QUEUED` (~35 min) then runs
  and COMPLETEs. `kaggle quota` moved off zero (GPU 0.02 h), which is the durable
  proof it ran on real silicon.
- **`NvidiaL4` (GPU L4 x4) is silently refused.** The run starts immediately,
  never queues, has no `nvidia-smi`, reports `torch 2.11.0+cpu`, and leaves
  `kaggle quota` at GPU 0.00 h used. The request is accepted and stored but never
  honoured. This kills the 96 GB Flash-Next plan on Kaggle.
- **T4 session:** 2× Tesla T4, **15360 MiB each (15 GB per card, NOT pooled)**,
  cc 7.5, driver 580.178.04, CUDA 12.8, `torch 2.11.0+cu128`. Turing: fp16 only,
  no bf16, no FA2.
- **RAM:** cgroup-capped at 30 GB (`/sys/fs/cgroup/memory.max = 32212254720`);
  `/proc/meminfo` reports the host 32.8 GB, so anything reading meminfo
  overestimates what it can use.
- **CPU:** 4 vCPU Xeon @2.0 GHz, AVX-512f present, `avx512_vnni`/`avx512_bf16`
  absent. Runs as uid 0 (root).
- **Disk:** the container root `/` is a writable overlay with ~1.1 TB free
  (~3.6 GB/s write); `/tmp`, `/root`, `/opt` inherit it. Only `/kaggle/working`
  persists as output. There is no `/kaggle/temp`. A 70 GB model can be
  downloaded into a session.
- **HuggingFace:** reachable, ~27+ MB/s measured, so 40 GB in ~25 min, 70 GB in
  ~43 min. `ISTA-DASLab/Qwen3.8-Flash-Next-GGUF` is 401 gated; use
  `unsloth/Qwen3.8-Flash-Next-GGUF` (open).
- **`ulimit -l` (RLIMIT_MEMLOCK) = 8 MB, soft AND hard.** This blocks any engine
  that pins tens of GB of host RAM.

The dense 27B question: two T4s do not make it faster. Generation is
layer-sequential across cards, and a dense model is capped by memory bandwidth
(~320 GB/s against ~9.4 GB read per token), the same wall the Colab T4 hit at
~8 t/s. MoE with small active params is the only speed lever here.

Next atomic action: read the memlock probe verdict (`pujan3645/strata-probe-2-memlock`),
record it here and in `docs/compute/kaggle.md`, then publish this checkpoint.

## Handoff

The Kaggle CLI is a uv tool at `C:\Users\pujan\.local\bin\kaggle`; it needs
`KAGGLE_API_TOKEN` exported in the same shell each call (shell state does not
persist between tool calls). Push with `kaggle kernels push -p <dir>`; the push
can rename the kernel slug and warns — always use the slug the push printed.

Private probe kernels left on the account, to be deleted on the owner's
go-ahead: `l4x4-probe`, `t4-probe`, `strata-probe`, `strata-probe-2-memlock`.

Do not request an AGENTS.md compute exception unless the memlock verdict is green
and a real eval run uses this path. Do not clone the repository to a Kaggle VM.
