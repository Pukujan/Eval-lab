# EXP-20261006-033 — LegalBench answer-key subset

**Status:** preregistered (frozen source, no model scored)
**Tracked by:** GitHub issue #94 (TASK-0069)
**Source:** LegalBench `nguha/legalbench@daec8237410aa23e3faf4bc41ad8b3a7e1696826`

This experiment widens the legal objective axis beyond the single LegalBench
Hearsay task (EXP-028, which stays unchanged) by adding three pinned answer-key
subtasks:

- `overruling` — is the cited sentence overruled? (CaseHOLD; CC BY 4.0)
- `definition_classification` — does the sentence define the term? (Kevin Tobia;
  CC BY-SA 4.0)
- `citation_prediction_classification` — does the citation support the sentence?
  (Livermore & Rockmore; CC BY 4.0)

Gold is the LegalBench answer key (`GoldProvenance.ANSWER_KEY`); no model
judgment is promoted to gold. Each task keeps a per-task verifier id.

## Licensing

The verbatim source files under `source/` are redistributed under their own
per-task licenses, which differ: `overruling` and
`citation_prediction_classification` are CC BY 4.0; `definition_classification`
is CC BY-SA 4.0 (see `source/LICENSE-NOTICE.txt` and
`source/definition_classification/LICENSE.txt`). These source licenses govern
the copied task data and are not superseded by the repository's own license.

## Split policy

The split unit is the case, keyed by the SHA-256 of the normalized `text`, so
every row sharing a text shares one `source_problem_id` and one split and no
case crosses the calibration/test boundary. This matters for
`citation_prediction_classification`, whose test rows repeat the same text with
opposite answers; a row-level split would place near-identical prompts on both
sides.

## Byte pinning

`source-manifest.json` and `experiment.yaml` pin SHA-256 digests of exact bytes:
the source files under `source/` and the canonical dataset. Both the pinned
source and the canonical dataset are LF-only. `core.autocrlf=true` (this repo's
setting) would otherwise rewrite them to CRLF on checkout and break the hashes,
so `.gitattributes` pins `experiments/EXP-20261006-033-legalbench-answer-key-subset/**`
to `text eol=lf` and the build writes every artifact with `newline="\n"`. The
preregistered dataset fingerprint is
`sha256:e756b17bbbe301d53f43ab3cd0e3bea72812b6c30db354698a1a545d636cb3d7`.

## Label contract

The shared single-mode path defaults to a `pass`/`fail` label space and coerces
`yes`/`no`. This subset keeps native `Yes`/`No` gold and records the
`label_set: ["Yes", "No"]` contract in `typed-question-spec.json`, to be scored
through the typed-spec path rather than the default pass/fail path. No runner is
added or changed here; that is a non-goal.

## Artifacts

`source-manifest.json`, `source/`, `canonical-records.jsonl`, `records.jsonl`,
`split-manifest.json`, `typed-question-spec.json`, `pool-manifest.json`,
`pool-checksums.sha256`, and a gold-only `report.md` stating each task's
majority-label baseline.

## Stopping rule

Do not score the blind partition until the source manifest, canonical dataset,
split manifest, typed-question spec, and fingerprints are committed.

## Limits

Three binary answer-key tasks, not a general legal-reasoning score. The
`definition_classification` task page reports one more test row than the pinned
machine-readable source; the source is preserved as distributed and no record is
fabricated. `citation_prediction_classification` has an exact 50/50 majority tie.
