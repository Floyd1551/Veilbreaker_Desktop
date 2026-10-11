# Android Capture Contract and Desktop Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Review and import versioned Android cellular snapshots into Desktop while retaining source evidence and optional future GPS metadata.

**Architecture:** A strict format parser feeds an explicit observation/cell selection UI and a worker import action. Only selected serving-cell measurements enter the diagnostic engine; the original envelope remains an evidence artifact. This is stage 1 of the approved design; companion capture and survey attachment receive separate implementation plans after the import contract is proven.

**Tech Stack:** Existing Python, unittest, PySide6, SQLite and evidence-manifest code; no new runtime dependency.

**Spec:** `docs/superpowers/specs/2026-10-10-android-cellular-design.md`

## Global constraints

- Format `veilbreaker.android.cellular`, schema version 1; UTF-8 JSON.
- Maximum 16 MiB, 1,000 observations, 256 cells per observation.
- Do not start acquisition, mix subscriptions, or substitute a neighbor for a serving cell.
- Preserve source bytes and unavailable values; normalize only supported quantities.
- Optional GPS data is preserved and validated, not collected or mapped in this phase.
- Existing flat-metric import and modem workflows must remain functional.

## Review focus

- Source modified between preview and import: reject the changed hash before writing a run.
- Dual-SIM or multiple registered cells: require explicit selection without strongest-cell fallback.
- Cached/future modem timestamps: show age/unknown without claiming fresh acquisition.
- Unknown GPS versus legitimate zero coordinates: preserve the distinction.
- Failed import or duplicate capture: no partial history entry; repeated import must be explicit and retain source ID.

## Task 1: Versioned contract and validation

**Files:** create `src/veilbreaker/android_capture.py`, `docs/android-capture-v1.md`, `examples/android-cellular-v1.json`, `tests/test_android_capture.py`.

**Interfaces:** `load_capture(path: Path) -> dict` returns `envelope`, `raw_bytes`, `sha256`; `validate_capture(value: dict) -> None` raises ValueError on invalid data. `normalize_selection(envelope: dict, observation_id: str, cell_index: int) -> dict` returns `metrics`, `provenance`, `notes`.

- [ ] Write contract fixtures and failing tests for invalid version/type, exact size and count limits, duplicate IDs, nonfinite values, Android sentinel values and invalid subscription references. Define exact identity/signal field names and units in the contract document before implementing normalization.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p test_android_capture.py`; confirm the missing implementation fails.
- [ ] Implement bounded byte loading, JSON validation and exact source hashing. Reject duplicate JSON keys. Preserve unknown fields only in the original envelope; never interpret them as metrics.
- [ ] Add selection tests: LTE RSRP maps to `lte_rsrp`; NR SS and CSI remain distinct; no neighbor/ambiguous registration selection, cross-SIM merge, or cached-to-fresh conversion. Implement explicit serving-cell normalization with per-field provenance.
- [ ] Add GPS tests for absent location, valid (0,0), out-of-range coordinates, negative accuracy, unavailable coordinates and unknown altitude datum. Validate the optional extension without using it for analysis.
- [ ] Run the contract tests to PASS and commit the contract, implementation and fixtures.

## Task 2: Evidence-preserving Android import worker

**Files:** create `src/veilbreaker/android_import.py`, `tests/test_android_import.py`; modify `src/veilbreaker/jobs.py` and narrowly extend the existing evidence/report save path in `src/veilbreaker/core.py`.

**Interfaces:** `import_capture(config, path: str, expected_sha256: str, observation_id: str, cell_index: int) -> dict` returns the existing desktop diagnostic payload with imported collection provenance. Worker action `android_import` calls this interface.

- [ ] Write failing tests using temporary storage: original bytes appear in the evidence manifest; selected observation and source hash remain traceable; hardware/network collectors are never called; import does not add host metrics.
- [ ] Add changed-source-hash and invalid-selection cases that create no run. Add repeated-capture handling that reports an existing import and requires an explicit repeat option rather than silently overwriting it; extend the interface with `allow_repeat: bool = False` for that purpose.
- [ ] Implement source verification and normalized analysis before committing history. Write original capture, mapping and provenance before the evidence manifest. Mark collection as imported, preserving partial/cancelled source status in provenance rather than claiming successful live capture.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p test_android_import.py`; expect PASS and verified evidence bundles. Run existing evidence and import-related regression tests; commit.

## Task 3: Native review and import workflow

**Files:** create `src/veilbreaker/android_ui.py`, `tests/test_android_ui.py`; modify `src/veilbreaker/gui.py` to add a dedicated Android capture action.

**Interfaces:** `AndroidImportDialog(parent, capture: dict)` exposes `selection() -> tuple[str, int] | None`; the caller dispatches the worker only after explicit import. The capture argument is the result of `load_capture`.

- [ ] Write failing Qt tests for device/subscription/time display, explicit observation and serving-cell selection, disabled import for absent/ambiguous selections, cancel-without-import and selected-cell payload. Show raw neighboring observations separately.
- [ ] Implement the dialog with read-only tables and clear cached/unavailable/partial labels. Show optional location as metadata only. Display the destination site/scenario and source hash; do not hide cross-device provenance.
- [ ] Wire import to the existing cancellable worker and result display. Handle known duplicate imports with an explicit repeat choice. Preview must not create history or call acquisition.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p test_android_ui.py`; expect PASS. Inspect a synthetic LTE/NR multi-SIM capture visually and reopen its saved report/evidence.
- [ ] Commit the UI and documentation. Record this as Desktop import support using synthetic fixtures, not physical Android qualification.

## Task 4: Release and next-phase handoff

- [ ] Run focused contract/import/UI and relevant existing evidence tests. Document results and unqualified device/platform combinations.
- [ ] Update README and roadmap with transfer/import instructions and the GPS extension boundary; increment release metadata only for the delivered Desktop feature.
- [ ] Build Windows package and installer through existing scripts; preserve skipped-test labeling if full qualification is not run. Commit and push source under existing user authorization.
- [ ] Prepare the companion implementation plan against the proven contract. Android API guards, foreground permissions, bounded sessions, cancellation and export remain required before the phone can produce real captures. Survey attachment follows that end-to-end validation; no phone/scanner compatibility claim before evidence exists.

## Execution record — October 10, 2026

Implemented contract validation, evidence-preserving worker import, explicit native selection UI and release documentation. Android-specific tests: 10 passed; evidence tests: 8 passed; existing GUI tests: 14 passed. Native worker import → history reopening → saved HTML report passed using the synthetic fixture. Preview screenshot: test-artifacts/android-import-preview.png.

Ruling: preserve every known signal quantity in the original capture; normalize only selected LTE/NR serving fields. Historical case/baseline matching and generic Android history deltas are withheld because receiver compatibility is not established. Costs: reduced automatic comparisons until a qualified compatibility rule exists.

Ruling: duplicate capture ID requires explicit repeat even when choosing another snapshot; this prevents accidental repeated imports while allowing deliberate per-observation analysis. Repeats keep independent run IDs.

Ruling: failure after artifact creation can leave unreferenced evidence files, but history is committed only after successful report/manifest generation. Original source files are never changed. No automatic deletion of potentially useful evidence occurs.

GPS coordinates are preserved only when present in the input; no location collection or mapping was added. Physical Android acquisition, companion APK and survey attachment remain separate phases.

Final review October 11: fixed selected-cell aliases so RF diagnosis receives imported RSRP/RSRQ (and NR SS-SINR only); excluded Android imports before desktop baseline limits and excluded Android confirmed cases from automatic matches; malformed enum types now raise validation errors. Android suite now 11 tests, engine suite 12 tests; evidence/GUI regression checks repeated.
