# EXP-032 — Jev as a closed-set GLEIF classifier

## Status

Preregistered. No blind split has been scored. The classifier dataset, results,
and report are intentionally absent until the preregistration and dataset
freeze are committed.

## Research question

Used as a typed `choice` over an explicit, closed label set, is Jev 1.13 a
usable multi-class classifier over frozen GLEIF registry fields — and does its
native probability vector support calibrated, selective prediction?

This is the classifier form of the question EXP-026 answers only in the binary
claim-verification form (`pass`/`fail`).

## Families

| Family | Classes | Role |
|---|---:|---|
| Entity category | 6 | Primary |
| Registration status | 7 | Secondary, deliberately hard |
| Legal jurisdiction | top-N + OTHER | Secondary, coverage/abstention |

Gold for every family is the frozen GLEIF source field value
(`deterministic_verifier`). No model judgment is promoted to gold.

## Primary comparison

Each family is scored against a **majority-class baseline** reported beside every
arm. Because entity category is ~92.5% GENERAL in a non-blind sample, raw
accuracy is misleading; balanced accuracy and macro-F1 are the honest headline.

## Stopping rule

Do not score the blind split until the task file, `experiment.yaml`, the
classifier dataset, the entity-disjoint split manifest, and the frozen
fingerprints are committed. Provider, parse, timeout, and rate-limit statuses
stay separate from labels.
