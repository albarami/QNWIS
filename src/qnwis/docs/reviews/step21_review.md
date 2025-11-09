# Step 21 Review & Hardening

## Highlights
- Enforced deterministic audit packs: canonical JSON, sorted freshness, and optional HMAC verification via `QNWIS_AUDIT_HMAC_KEY`.
- Segmented evidence with deterministic filenames plus deduplicated `sources/*.json` descriptors and PII-redacted narratives/snippets.
- Replay stubs (`replay.json`) capture sanitized task/routing metadata for offline dry-runs; CLI `qnwis_audit prune` manages retention windows.
- SQLite store now versioned (user_version pragma), WAL-enabled, and exposes safe upserts/deletes; FileSystem store indexes external packs.
- Format node renders a compact Audit Summary (ID, top sources, integrity, artifact counts). Verify node now writes audit packs even on ERROR paths.
- CLI `verify` honors per-config HMAC envs, accepts `--path`, and surfaces digest mismatches; unit/perf suites extended to guard <500 ms pack writes.

## Miniature Pack Tree
```
audit_packs/00518c6b-8dc0-491a-bd62-8ced07a6e2c5/
├── manifest.json
├── narrative.md
├── replay.json
├── reproducibility.py
├── evidence/
│   └── qid_review_001.json
├── sources/
│   └── review_dataset.json
└── verification/
    └── citations.json
```

## CLI Verify Snapshot
```
$ python -m src.qnwis.cli.qnwis_audit verify --path audit_packs/00518c6b-8dc0-491a-bd62-8ced07a6e2c5
2025-11-07 13:15:40,434 - src.qnwis.verification.audit_trail - INFO - Audit trail initialized: pack_dir=D:\lmis_int\audit_packs
[OK] 00518c6b-8dc0-491a-bd62-8ced07a6e2c5
```

## Test Notes
- `python -m pytest tests/unit/audit` (includes new perf guard) ✅
- `python -m pytest tests/integration/audit/test_audit_end_to_end.py` ➜ existing fixture recursion in `mock_exists` (pre-existing; manifests still produced manually for verification output above).
