# Map packs and report imagery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Manage local map packs and prepare self-contained photographic survey reports.

**Architecture:** Keep basemap registrations in local settings. Store bounded source imagery and provenance beneath the survey assets directory; derive a portable annotated PNG for both report viewers. Online NAIP preparation is explicit and shares the offline import validation path.

**Tech Stack:** Python, PySide6, SQLite-backed existing survey records, standard-library HTTP/JSON, existing PMTiles renderer.

**Spec:** ../specs/2026-10-20-map-packs-report-imagery-design.md

## Global constraints

- Maximum source image dimension 2048 pixels; maximum download 20 MiB.
- Viewing/exporting never downloads imagery.
- Report rendering uses a bounded 1440×800 PNG compatible with the current offline viewer; increase its encoded-image cap only as needed, retaining decoded bounds.
- Preserve original run evidence and previous valid imagery on failure.
- Aerial imagery is labelled aerial, never live or satellite.
- Reference/tower/LOS features are outside this increment.
- Execution: implement directly in this session under the user's instruction to move to implementation.

## Review focus

- Decompression bombs, malformed georeferencing and invalid/nonfinite coordinates: reject before drawing.
- Changed survey points: show stale-overlay status and regenerate explicitly.
- Missing asset files: old surveys still open/export with a readable explanation.
- Provider timeouts, oversized bodies and cancellation: no partial replacement.
- Embedded image safety: no external or unrelated local file access in report viewing.

### Task 1: Local pack catalog

Files: create `src/veilbreaker/map_catalog.py`; modify `map_pack.py`, `map_ui.py`; test `tests/test_map_catalog.py`.

Interfaces: `PackCatalog(path).register(pack_path) -> dict`, `.entries() -> list[dict]`, `.remove(pack_path) -> None`; validator additionally returns header bounds. Catalog entries store absolute path, name, bounds, zooms, size and registration timestamp.

- [ ] Write tests for registration, duplicate replacement, missing files, unregister preserving archive.
- [ ] Run focused unittest discovery and observe missing-module failure.
- [ ] Implement atomic catalog writes, a saved-pack selector, remove registration and re-import/relink.
- [ ] Verify focused tests and existing map UI tests; commit.

### Task 2: Georeferenced source imagery and annotation

Files: create `src/veilbreaker/survey_imagery.py`; test `tests/test_survey_imagery.py`.

Interfaces: `validate_metadata(meta) -> dict`; `decode_image(raw) -> QImage`; `survey_points(config,path) -> list[dict]`; `render_image(raw,meta,points) -> bytes`; `save_imagery(config,path,raw,meta,points) -> dict`; `load_imagery(config,path) -> dict|None`.

Metadata schema: version 1, bounds `[west,south,east,north]`, CRS EPSG:4326 or EPSG:3857, source, attribution, imagery_date (nullable), prepared_utc. Bounds are image outer edges; north-up only. Reject reversed/degenerate or out-of-range extents, unsupported CRS, invalid text and oversized bytes/dimensions.

- [ ] Tests cover valid PNG/JPEG, bad bounds/nonfinite values, excessive dimensions, known marker placement and missing GPS.
- [ ] Observe RED; implement Qt image decoding with dimension preflight, projection, numbered markers, north arrow and ground-distance scale.
- [ ] Store versioned immutable source/overlay/metadata assets and atomically replace the survey attachment pointer under the existing survey lock. Keep original evidence untouched.
- [ ] Test previous attachment survives failure, path confinement, missing assets and changed-position fingerprints; commit.

### Task 3: Offline report embedding and export

Files: modify `survey_report.py`, `survey.py`, `survey_ui.py`, `report_viewer.py`; test `test_survey_imagery.py`, `test_survey_report.py`, `test_report_viewer.py`.

Interfaces: `report_context(config,path) -> dict|None` loads verified cached overlay plus provenance and staleness warning; `report_html(session, imagery=None)` accepts this optional context without changing old callers.

- [ ] Tests assert base64 embedding, escaping attribution, old-session compatibility, missing/stale image warnings and offline browser decode.
- [ ] Observe RED, implement Survey area section near report start, and use identical context in native viewing and exported HTML.
- [ ] Include attached source/overlay/metadata in new survey ZIPs before manifest creation; test hashes and relocated report usability.
- [ ] Verify focused tests; commit.

### Task 4: Explicit preparation UI and NAIP adapter

Files: create `src/veilbreaker/imagery_provider.py`, `src/veilbreaker/survey_imagery_ui.py`; modify `survey_ui.py`; test `tests/test_imagery_provider.py`, `tests/test_survey_imagery_ui.py`.

Interfaces: `fetch_naip(bounds, cancelled, progress=None) -> (bytes, dict)`; `SurveyImageryDialog(parent,config,path)` handles extent preview, offline image+sidecar selection, explicit fetch, preview and Save.

- [ ] Tests pin request endpoint/CRS/size, streamed byte limit, timeout, cancellation, provider error response and provenance.
- [ ] Inspect real USGS service metadata before implementing request parameters; no invented acquisition dates.
- [ ] Use a finite-timeout cancellable worker with explicit Qt slots, retaining the dialog until the worker finishes. Download only after the user presses the labelled online action; send bounds, never phone identity.
- [ ] Add Prepare report map and preview with bounds, point counts and source/date. Manual area selection is labelled when no qualified GPS exists.
- [ ] Verify offline import/save, failure preservation, responsive cancellation and one small public-area real provider sample; commit.

### Task 5: Release qualification

Files: `docs/offline-maps.md`, release notes, version metadata.

- [ ] Whole-change review; resolve actionable correctness issues with regression tests.
- [ ] Full unittest suite, native report image inspection, packaged GUI/map checks and installer.
- [ ] Record actual validation and limitations; commit and push under existing authorization.


## Execution record

Tasks 1–4 implemented together on `codex/map-report-imagery`; one consolidated
feature commit is used instead of the suggested intermediate commits. Focused
RED/GREEN checks were observed for catalog, imagery, reports and provider. The
Qt dialog check exposed a collision with QDialog.finished; its completion slot
was renamed and cancellation passed. Independent review found Unicode text
corruption and missing-GPS membership staleness; both were corrected.

Verification: 209 tests passed; real Dallas NAIP download and native report
inspection passed; 20-point native preparation preview passed. Portable release
0.36.0rc1 passed frozen CLI, Unicode worker, six-page GUI and offline map checks.
Windows installer compilation and checksum verification completed. Implementation
commit 3e1ab51 was fast-forwarded and pushed to GitHub main.
