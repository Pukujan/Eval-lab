# Experiment 1 public evaluation

Eval-lab receives a materialized `evidence-intake/1.0.0` directory. Intake validates the exact released schema, canonical manifest digest, declared regular-file set, byte counts, artifact hashes, attempt lineage, visible-test count reconciliation, redaction records, and model-proxy audit before any candidate code is executed.

For the approved duplicate-processing fixture, the evaluator checks the frozen JobSpec digest and requested/resolved model identities, permits changes only to `src/processor.py` or `src/store.py`, applies the candidate diff to a clean public fixture copy, compiles it, runs the visible suite independently, and runs the public irreversible-effect probe. The known duct-tape store change is rejected because it still records two effects and two raw result rows even though the visible suite passes.

The first experiment runs no rubric scorer and invokes no private verifier. The emitted `evallab-outcome/1.0.0` report always requires human review, performs no merge or deployment, and classifies harness failures separately from failed patch gates.
