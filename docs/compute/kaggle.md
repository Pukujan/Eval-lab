# Kaggle CLI guide for eval-lab

Source of truth for running evals on the owner's Kaggle account. Written
2026-10-11 from real batch-kernel runs, not from documentation. Update it
whenever something changes.

## 1. What is installed and where

- Official `kaggle` CLI 2.2.4, installed as a uv tool **outside the repository**
  (per the AGENTS.md one-environment rule) at `C:\Users\pujan\.local\bin\kaggle`;
  package root `C:\Users\pujan\AppData\Roaming\uv\tools\kaggle`.
- Auth is a new-style access token (prefix `KGAT_`), read from the owner's
  Desktop config `.env` as `KAGGLE_API_TOKEN`. No `kaggle.json` and no
  username+key pair is needed — export the env var only.
- **Never print, upload, or commit the token.** Shell state does not persist
  between tool calls, so export it inline in every command:
  `export KAGGLE_API_TOKEN=$(grep -E '^KAGGLE_API_TOKEN=' <configs>/.env | cut -d= -f2- | tr -d '\r')`.
- Check quota: `kaggle quota` (GPU 30 h/week, TPU 20 h/week; one shared pool per
  accelerator family; resets weekly).

## 2. Account and accelerator facts (measured 2026-10-11)

Account `pujan3645`. Phone verification is **required** — before it, both GPU and
internet were silently dead.

| UI option | `machine_shape` | Hardware | Offered here? |
|---|---|---|---|
| GPU T4 ×2 | `NvidiaTeslaT4` | 2× Tesla T4, 15360 MiB each | **yes, confirmed** |
| GPU L4 ×4 | `NvidiaL4` | 4× L4, 24 GB each | **no — silently refused** |
| TPU v5e-8 | `TpuV5E8` | 8× TPU v5e | untested |

The Tesla P100 was retired 2026-09-15, so `enable_gpu: true` alone no longer
picks a sane default — set `machine_shape` explicitly.

**Diagnostic rule — never trust "push succeeded":**

- Run starts **immediately**, never queues, no `nvidia-smi`, `torch …+cpu`, and
  `kaggle quota` stays at 0.00 h → the accelerator was **silently refused**
  (this is what `NvidiaL4` does on this account).
- Run sits in `KernelWorkerStatus.QUEUED` for a while, then COMPLETEs, and
  `kaggle quota` moves off zero → the request was **real** and ran on silicon.

Always confirm with `kaggle quota` (non-zero GPU hours) and `nvidia-smi` in the
logs.

## 3. Rules and safety

- Use `kernel_type: script` (batch), not an interactive notebook. A script
  kernel runs top-to-bottom and the session **ends on its own** when the script
  exits, so there is no idle GPU to forget about — the "left it running
  overnight" failure mode does not exist on this path. Interactive notebooks can
  idle and are ended by Kaggle itself on an idle timeout (~20 min).
- Limits: 12 h max for CPU/GPU batch, 9 h for TPU.
- There is **no CLI `stop`/`cancel` command.** The SDK exposes
  `cancel_kernel_session`, but `kernel_session_id` was absent from the push
  response, so an external cancel watchdog is not straightforwardly wired up.
  Prefer batch kernels plus a self-imposed time guard inside the script.
- Never clone or copy the repository to a Kaggle VM. Only gold-free request
  files may be served there; scoring stays offline in the canonical `.venv`.

## 4. Driving it

- `kaggle kernels push -p <dir>` with a `kernel-metadata.json` (`id`,
  `title`, `code_file`, `language: python`, `kernel_type: script`,
  `is_private`, `enable_gpu`, `machine_shape`, `enable_internet`).
- Then `kaggle kernels status <slug>` / `logs <slug>` / `output <slug>`.
- Write results to `/kaggle/working` and pull them down; only that directory is
  persisted as kernel output.
- **Slug gotcha:** a push can RENAME the kernel from the metadata `id`. The push
  prints the real slug and warns, but does not update `kernel-metadata.json`. A
  watcher pointed at the intended slug then dies with "Permission 'kernels.get'
  was denied" — that is a wrong-slug error, NOT a terminal state. Always use the
  slug the push printed.
- `PYTHONIOENCODING=utf-8` avoids `UnicodeEncodeError` when decoding logs.

## 5. T4 session shape (measured 2026-10-11)

- **GPU:** 2× Tesla T4, **15360 MiB each (15 GB per card, NOT pooled)**, cc 7.5,
  driver 580.178.04, CUDA 12.8, `torch 2.11.0+cu128`. Turing: fp16 only, no
  bf16, no FA2.
- **RAM:** cgroup-capped at **30 GB** (`/sys/fs/cgroup/memory.max =
  32212254720`). `/proc/meminfo` reports the host 32.8 GB, so anything reading
  meminfo overestimates what it can use.
- **CPU:** 4 vCPU Xeon @2.0 GHz, AVX-512f present, `avx512_vnni`/`avx512_bf16`
  absent. Runs as **uid 0 (root)**.
- **Disk:** the container root `/` is a writable **overlay with ~1.1 TB free**
  (~3.6 GB/s write); `/tmp`, `/root`, `/opt` inherit it. `/kaggle/working` is
  capped at 20 GB and is the only persisted output. There is no `/kaggle/temp`.
  A 70 GB model can be downloaded into a session — put it on `/tmp` or `/`.
- **HuggingFace:** reachable, ~27+ MB/s measured → 40 GB in ~25 min, 70 GB in
  ~43 min. `ISTA-DASLab/Qwen3.8-Flash-Next-GGUF` is 401 gated; use
  `unsloth/Qwen3.8-Flash-Next-GGUF` (open).
- **`ulimit -l` (RLIMIT_MEMLOCK) = 8 MB, soft AND hard.** See §7.

## 6. What this path is good for

- **MoE models with small active params** — the same speed lever as on Colab.
  A 125B-class MoE reads only ~1–2B active params per token.
- **Not** the dense 27B GSQ-RCO. Two T4s do not help: generation is
  layer-sequential across cards, and a dense model is capped by memory bandwidth
  (~320 GB/s against ~9.4 GB read per token) — the same wall the Colab T4 hit at
  ~8 t/s. This is the direct answer to "will two T4s be faster": no.
- The L4×4 shape (96 GB) would have been the way to run Flash-Next densely, but
  this account is not offered it.

## 7. Strata and the pinned-memory blocker

Strata (`Niko1221/Strata`, MIT) is an MoE inference engine that keeps hot experts
in VRAM, pins the full expert set (23–50 GB) in system RAM, and computes misses
on the CPU. It is the plausible way to run the 125B MoE here — but it needs tens
of GB **pinned**, and this session's `RLIMIT_MEMLOCK` is 8 MB. Whether `root` +
`CAP_SYS_RESOURCE` can lift the cap in-container is the open question (probe
`pujan3645/strata-probe-2-memlock`, 2026-10-11). If red, Kaggle is T4-class
compute only and Strata is dropped.

Note: stock llama.cpp has its own expert offload (`--n-cpu-moe`), so a pivot away
from Strata is cheap.

## 8. How to record every run (required)

For each run, log: date/time, model repo + exact file + SHA256, quant, engine
and build/commit, accelerator, flags, pp/tg t/s, peak VRAM and RAM, max context
tested, quality notes, wall time per stage, problems, and confirmation the
session ended. Commit results in machine-readable form (JSONL/CSV) plus a short
markdown note, and link the GitHub issue.
