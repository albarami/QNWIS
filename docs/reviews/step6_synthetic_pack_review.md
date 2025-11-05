# Step 6 Synthetic Pack Review

## Diff Highlights
- `src/qnwis/data/synthetic/seed_lmis.py`: split generation into helper writers, added strict argument validation, clamped salary/attrition/drop outputs, and ensured deterministic RNG flow with shared state.
- `scripts/seed_synthetic_lmis.py`: new `--small` preset, runtime path bootstrapper, and cleaned CLI messaging for ASCII-only output.
- `data/catalog/datasets.yaml`: catalog entry for synthetic aggregates with `MIT-SYNTHETIC` license so provenance enrichment prefers the synthetic tag.
- `src/qnwis/data/deterministic/cache_access.py`: enrichment now falls back to dataset_id matching and always prefers catalog-provided licenses.
- `tests/integration/test_synthetic_seed_and_queries.py` & `tests/unit/test_synthetic_shapes.py`: tightened determinism assertions (full-file hashing), license expectations, bounds validation, and error cases for invalid generator inputs.
- `src/qnwis/data/queries/syn_*.yaml` & docs: normalized punctuation to ASCII and documented the fast `--small` preset for demos.

## Tests & Quality Gates
```
python -m pytest tests/integration/test_synthetic_seed_and_queries.py tests/unit/test_synthetic_shapes.py tests/unit/test_queries_yaml_loads.py
python -m ruff check src/qnwis/data/synthetic/seed_lmis.py scripts/seed_synthetic_lmis.py tests/integration/test_synthetic_seed_and_queries.py tests/unit/test_synthetic_shapes.py
python -m flake8 src/qnwis/data/synthetic/seed_lmis.py scripts/seed_synthetic_lmis.py tests/integration/test_synthetic_seed_and_queries.py tests/unit/test_synthetic_shapes.py
python -m mypy --explicit-package-bases src/qnwis/data/synthetic/seed_lmis.py scripts/seed_synthetic_lmis.py
scripts/secret_scan.ps1
```
All commands completed without findings after the generator refactor.

## Notes
- The synthetic pack now advertises `MIT-SYNTHETIC` provenance, keeps attrition/drop metrics inside 0–100, and enforces salary floors deterministically.
- Integration remains compatible with Steps 3–6 interfaces: the dataset catalog exposes the synthetic license, query IDs remain unchanged, and the CLI delivers both full and demo (`--small`) datasets while staying fully synthetic.
