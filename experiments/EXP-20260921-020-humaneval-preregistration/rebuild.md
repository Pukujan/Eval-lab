# Rebuild and verification boundary

From this repository worktree, verify the planning checkpoint with:

```powershell
python scripts/check_repo_contract.py
python -m pytest -q tests/test_repo_contract.py tests/test_program_contract.py tests/test_schema.py
ruff check .
git diff --check
```

Compare SHA-256 of `README.md`, `experiment.yaml`, `plan.md`, and `rebuild.md`
against `checksums.sha256`. The checksum file intentionally does not hash
itself. The Git commit records the task log and manifest identity.

No dataset, candidate, prediction, result or report can be rebuilt from this
planning-only skeleton. A later authorized checkpoint must pin source archive
and canonical-row digests, task split lists, candidate pool, adapter/verifier
version, sandbox image and proof, provider routes, and all remaining null
manifest fields. Rebuild commands for data and labels must be added only then,
without overwriting completed experiments. Never run untrusted candidate code
on the Windows host or in an unproven WSL environment.
