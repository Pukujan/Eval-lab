# EXP-20261004-030 — Grok Build harness correction

This experiment corrects a harness defect that invalidated the Grok Build
results in EXP-015, EXP-022, and EXP-025. It does not modify any of them.

## What was wrong

The shared runner built the Grok command as `--single=<prompt>`. The prompt is
two lines: one instruction line plus a JSON payload. On Windows,
`shutil.which("grok")` resolves to the `grok.CMD` shim, and `subprocess.Popen`
runs a `.CMD` through `cmd.exe`, which truncates the command line at the first
embedded newline. The model therefore received only the instruction line, with
no record payload, and collapsed to a constant answer: `fail` in single mode and
`TIE` in pairwise mode. This matches the recorded EXP-022/EXP-025 behaviour
(single accuracy ~0.50, pairwise accuracy ~0.02, mode-balanced score ~0.26).

## What changed

The only change is the provider invocation. The prompt is written to a unique
per-record temp file and passed as `--prompt-file <path>`; the file is removed in
a `finally` block. Records, gold labels, model aliases, JSON schema, route, and
timeout are identical to EXP-022.

## Evidence of the fix

Through the real runner code path (monkeypatching only the subprocess launcher):

| Mode | As-committed `--single` | Corrected `--prompt-file` |
| --- | ---: | ---: |
| single (16 public) | 9/16 | 16/16 |
| pairwise (8 public) | 0/8 (all `TIE`) | 8/8 |

Replacing the newline with a space also fixes the inline form, confirming the
newline (not the JSON quotes) is the trigger.

## Scope

- Public selection: the 648 frozen EXP-015 public records.
- Blind holdout: the 760 frozen EXP-015 blind records, run only after the public
  canary recovers both modes.
- Models: Grok 4.6 and Grok 4.7 through the direct authenticated `grok` CLI.

Provider errors, rate limits, timeouts, and parse ambiguity remain explicit
execution statuses and are never converted into labels. The blind holdout is not
used to select anything.
