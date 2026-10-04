# Google Colab CLI guide for eval-lab (free tier)

Source of truth for running evals on Alex's free Google Colab account. Written by colab-cli on 2026-10-04 from real runs. Keep it in the repo (suggested `docs/compute/colab-cli.md`) and update it whenever something changes.

## 1. What is installed and where
- Official CLI: `google-colab-cli` (https://github.com/googlecolab/google-colab-cli), Linux/macOS only.
- On Teresa-Pujan it lives in WSL distro `Ubuntu-22.04` (disk at `C:\wsl\Ubuntu-22.04\ext4.vhdx`), user root, binary `/root/.local/bin/colab`, installed with `uv tool install google-colab-cli`.
- Auth is done (oauth2 default). Session state: `~/.config/colab-cli/sessions.json` inside WSL. Never print or copy tokens.
- Check health: `colab usage` (balance, rate, active assignments) and `colab sessions`.

## 2. Account facts (measured 2026-10-04)
- Free tier: 0.00 compute units. Google AI Pro is a different subscription and gives no Colab units.
- Accelerators accepted: `--gpu T4` and `--tpu v5e1`. Rejected: L4, A100, H100, G4, v6e1.
- T4 VM: Tesla T4 15,360 MiB (~14.8 GB usable), 12 GB RAM, 2 vCPUs, ~71 GB free disk, Ubuntu 24.04, driver 580 / CUDA 13.

## 3. Rules (free tier ToS, Colab FAQ)
- No `colab ssh` or `colab console` on free tier (remote shells are banned there). Use `colab exec` / `colab run`.
- No tunnels (ngrok/cloudflared), no mining, no multiple accounts, no proxies, no cookie scraping.
- One session at a time. Always `colab stop -s <name>` at the end, even on failure, then confirm `colab sessions` shows none.
- Free runtimes are not guaranteed, time-limited and can be killed. Design evals to checkpoint results and resume.

## 4. Driving it from Windows (gotchas)
- Passing `bash -lc "..."` from PowerShell breaks on `$PATH` and parentheses in Windows paths. Write a bash script with a PowerShell here-string, strip CRs, and run it:
  `$s -replace "`r","" | Set-Content -NoNewline -Encoding ascii $env:TEMP\x.sh`
  `wsl -d Ubuntu-22.04 -- bash /mnt/c/Users/pujan/AppData/Local/Temp/x.sh`
- Redirect stdin from `/dev/null` for every colab command so nothing hangs on a prompt.
- Long steps: run in the background inside the runtime (`nohup ... &`) and poll with short `colab exec` calls; long exec calls can time out.
- Core commands: `new -s NAME --gpu T4`, `exec`, `run`, `upload`, `download`, `ls`, `install`, `log`, `sessions`, `status`, `stop`, `usage`. Use `colab <cmd> --help`.

## 5. llama.cpp on the T4 (works, no compile)
- Use the official prebuilt Linux CUDA 12.x release of llama.cpp (tested b11398/b11399).
- Set `LD_LIBRARY_PATH` to include the bundled lib folder AND `/usr/lib64-nvidia`, or CUDA libs aren't found.
- Pass `-t 2` (it defaults to 1 thread on the 2-vCPU VM). Use `-ngl 99` for full GPU offload.
- First load of a big GGUF can print nothing for 2–3 minutes. It isn't hung.
- HF downloads run at ~70 MB/s (10 GB in about 2.5 min).

## 6. Results so far (llama-bench pp512 / tg128, 3 reps)
| Model | File | Where it ran | Prompt t/s | Gen t/s | Peak VRAM | Max ctx |
|---|---|---|---|---|---|---|
| Qwen3.8-27B GSQ-RCO | IQ3_XXS 10.1 GB (ISTA-DASLab/Qwen3.8-27B-GSQ-RCO-GGUF) | T4 GPU | 253–266 | 8.1–8.6 | 10.3 GB | ~64K (128K OOM) |
| Maple Preview 20B-A1B | official TQ2_0-head-Q4_K 5.5 GB (deepgrove/maple-preview-GGUF) | CPU only (no CUDA TQ2_0 kernels in stock llama.cpp) | ~41 | 21–23 | 0.7 GB | 128K |
| Maple Preview 20B-A1B | requantized to Q2_0, Q4_K head, 6.4 GB | T4 GPU | 2,094–2,282 | 199–212 | 5.9 GB | 128K (7.5 GB) |

- Maple conversion: `llama-quantize --allow-requantize` from TQ2_0 to Q2_0 keeping the Q4_K output head, ~191 s on the VM. Lossless per a llama.cpp reviewer. The file is lost when the session stops, so save it (Drive or HF) or redo it each run.
- Both models passed a merge_intervals coding prompt. Benchmark claims (AIME26, GPQA, LCBv6) are NOT verified yet.

## 7. T4 vs TPU (why the T4 is the eval box)
- A dense 27B on a T4 is capped by memory bandwidth (~320 GB/s against ~9.4 GB read per token), and IQ formats decode slowly on Turing, which explains ~8 t/s. MoE models with small active params (Maple, ~1B active) are fast.
- TPU v5e (16 GB HBM, ~820 GB/s) only runs JAX / vLLM-TPU with plain bf16/int8/limited int4. It cannot run GGUF, IQ, or ternary quants. Qwen 27B won't fit (27 GB even at int8). Maple at 20B needs ~10 GB at int4 plus architecture support, unverified and unlikely to beat 200 t/s.
- Running GSQ-RCO/IQ weights on a TPU would need custom Pallas kernels plus a JAX model port: weeks of research work, best case 2–3x.
- OpenJev (openjev/openjev, dense 27B): smallest official GGUF is Q4_K_M 16.5 GB, too big for a T4. An IQ3 requant (~10–11 GB) should fit. It needs one output token per decision, so prompt speed (~260 t/s) dominates: an estimated ~6 s per 1,500-token decision. Untested.
- vllm.cpp (phantomic12 fork of mudler/vllm.cpp): no TPU backend, no TQ2_0 GGUF loading yet. Only worth testing for multi-request serving.

## 8. How to record every run (required)
For each run, log: date/time ET, model repo + exact file + SHA256, quant, llama.cpp build/commit, accelerator, flags (ngl, fa, ctx, threads), pp/tg t/s, peak VRAM, max ctx tested, quality notes, wall time per stage, problems, and confirmation the session was stopped. Commit results in machine-readable form (JSONL/CSV) plus a short markdown note, and link the GitHub issue.
