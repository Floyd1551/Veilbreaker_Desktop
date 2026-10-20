# Cell-reference matching implementation plan

> **For agentic workers:** Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development if the user selects delegation. Implement task-by-task.

**Spec:** ../specs/2026-10-20-tower-matching-terrain-design.md (approved by user).

**Goal:** Match captured serving-cell identities to offline references and save map/report context without altering original evidence.

**Architecture:** Immutable indexed SQLite reference snapshots with an atomic active pointer; observation-specific matching; derived attachment snapshots for repeatable offline reports. Terrain is a separate subsequent plan.

**Tech Stack:** Python standard library SQLite/CSV/gzip, PySide6, existing MapLibre bridge and survey export.

## Global constraints

- No PCI-only or nearest-site matching. Preserve conflicting locations.
- OpenCellID initial adapter is LTE only. Operator records may explicitly carry LTE/NR.
- No implicit data downloads, credential collection, or new inference of physical towers.
- GPS is taken from the same observation as the cell, with existing quality rules.
- Import ceiling: 20 million rows, 8 GiB decompressed input, 64 KiB per record;
  staging stops below 512 MiB free disk, checked every 10,000 rows.
- Worker signals use explicit QObject slots; close waits for cancellation completion.

## Review focus

- Duplicate identities and leading-zero network identifiers must not pick arbitrary sites.
- Later observations must not supply missing identity fields to earlier cells.
- Corrupt gzip or disk errors must leave the active snapshot unchanged.
- Removed reference data must not invalidate already-exported context.
- Map asset hashes must be regenerated after app.js changes without rewriting vendored files.

### 1. Validated reference snapshots

Files: create `src/veilbreaker/cell_reference.py`, `tests/test_cell_reference.py`.
Interfaces: `import_reference(root, source, metadata, cancelled, progress) -> dict`,
`activate_reference(root, dataset_id)`, `list_references(root) -> list`,
`lookup_reference(root, key) -> list[dict]`. Root is `config.root / 'cell-references'`.
`key` is `(radio, mcc, mnc, tac, cell_id)` with integer components except radio.
Snapshot manifests include SHA-256, adapter/schema version, source/license/date,
counts and UUID; never accept a caller-supplied path as dataset ID.

- [ ] Write tests for valid LTE CSV/GZIP, operator LTE/NR JSON, invalid ranges,
  wrong headers, diff filenames, decompression truncation, conflicting duplicates,
  repeat SHA import, cancellation and failed activation preserving old data.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p test_cell_reference.py`; observe RED.
- [ ] Implement streaming validation, temporary SQLite transactions and atomic activation.
  LTE TAC is 0..65535 and ECI 0..268435455; NR TAC 0..16777215 and NCI
  0..68719476735 for operator input. Reject booleans and floating identity values.
  MCC 100..999, MNC 0..999; retain original textual identity alongside normalized key.
  Validate bounded operator JSON (8 MiB, 10,000 records) with source and verification label.
- [ ] Run focused tests GREEN, including monkeypatched small limits and disk failure; commit.

### 2. Observation-specific matching

Files: create `src/veilbreaker/cell_matching.py`, `tests/test_cell_matching.py`.
Interfaces: `match_capture(envelope, reference_root) -> dict`,
`load_run_matches(config, run_id) -> dict`. Each result retains observation ID,
subscription, cell index, original identity/signal, location quality, modem/GPS offset,
status and all reference candidates. Capture loading uses existing `load_capture`.

- [ ] Write tests for exact LTE match, wrong TAC/network/radio, missing identity,
  unsupported NR source, PCI-only input, conflicting sites and observation separation.
  Assert an unqualified same-observation GPS produces no distance/bearing even if
  another observation has good GPS. Test multiple SIMs and missing capture files.
- [ ] Observe RED with `test_cell_matching.py` discovery.
- [ ] Implement qualified registered-cell matching only. Compute distance and initial
  bearing using a documented spherical Earth radius 6371008.8 m; label approximate.
  Do not merge nullable fields across observations or use SIM carrier as identity.
- [ ] Verify tests GREEN and existing Android/report tests; commit.

### 3. Reference management and map selection

Files: create `src/veilbreaker/cell_reference_ui.py`; modify `map_ui.py`, `map_sources.py`,
`gui.py`, `assets/maps/app.js`; create `tests/test_cell_reference_ui.py`.
Interfaces: `CellReferenceDialog(parent, config)` imports/activates records;
`MapWindow` receives optional config, preserving existing smoke-test callers.
Extend map model with `cell_candidates` and `bearing_lines` GeoJSON collections;
existing GPS features remain unchanged. GeoJSON properties carry plain display data only.

- [ ] Write Qt tests for import success/failure/cancel, snapshot switching, missing
  database, selected observation filtering, conflicting candidate selection and no-GPS state.
- [ ] Observe RED, then implement **Cell references** and **Match serving cells** actions.
  Show selected-run results in a native table; cap visible candidate features at 200
  with an explicit omitted count. Receiver/candidate symbols differ; lines say bearing.
- [ ] Add MapLibre layers and retain the native table when renderer is unavailable.
  Update the map asset manifest using the existing vendor/hash workflow without
  downloading or changing unrelated bundled assets.
- [ ] Run focused GUI/map tests and real native rendering; commit.

### 4. Saved context and portable reports

Files: create `src/veilbreaker/cell_context.py`, `cell_context_report.py`,
`tests/test_cell_context.py`; modify `survey_ui.py`, `survey.py`, `survey_report.py`.
Interfaces: `save_context(config, survey_path, matches) -> dict`,
`load_context(config, survey_path) -> dict|None`, `context_html(context) -> str`.
Immutable UUID assets beneath survey-owned storage; journal pointer updated under
session lock. Snapshot records retain reference attribution/license, source hashes,
original capture hashes and matcher version. No original run bundles are rewritten.

- [ ] Tests pin escaped output, saved candidates, unchanged original evidence,
  missing/corrupt attachments, stale capture/membership fingerprints, exported hashes,
  and report usability after deleting the live reference registration.
- [ ] Observe RED; implement explicit **Save cell context to survey** and render the same
  context in native HTML and new survey exports. Non-survey run context can be viewed
  and saved as standalone HTML/JSON from the result dialog.
- [ ] Verify tests GREEN and export relocation; commit.

### 5. Matching release gate

- [ ] Independent review; fix actionable issues and add regression tests.
- [ ] Run full unittest discovery, native import/match/report inspection, frozen GUI/map
  and worker checks. Use synthetic references until authorized real data is supplied;
  do not claim verified serving-tower identification from synthetic fixtures.
- [ ] Document schema, offline flow and limits; version, build installer, checksum,
  commit/push. Continue with the terrain plan after matching is independently usable.
