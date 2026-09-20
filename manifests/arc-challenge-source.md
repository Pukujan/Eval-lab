# ARC-Challenge source note

- Dataset: `allenai/ai2_arc`
- Configuration: `ARC-Challenge`
- License recorded from Hugging Face metadata: `CC BY-SA 4.0`
- Requested revision: `main`
- Resolved revision for the committed six-record slice: `210d026faf9955653af8916fad021475a3f00453`
- Canonicalization: `arc-challenge-canonical-v1`
- Slice manifest: `arc-challenge-slice.json`
- Retrieval: `resolve_arc_source_metadata()` pins the revision through the Hugging Face dataset metadata API; `load_arc_rows()` then requests only the selected split at that commit.
- Initial slice policy: two rows from each upstream `train`, `validation`, and `test` split. Validation rows map deterministically to `dev` or `calibration` by source ID and seed `20260920`.

The dataset cache and raw rows are not committed. The JSON manifest records the source facts, canonical record IDs, split counts, and output fingerprint needed to reproduce this slice.
