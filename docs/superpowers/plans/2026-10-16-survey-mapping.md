# GPS Survey Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans for native implementation, or superpowers:subagent-driven-development if the user selects delegated execution. Steps use checkbox syntax for tracking.

**Goal:** View saved diagnostic and survey GPS evidence on an offline desktop map, inspect uncertainty, and open associated diagnostics.

**Architecture:** Derive a GeoJSON model from existing evidence. Serve pinned MapLibre assets and an explicitly selected PMTiles archive through a restricted local service; display them in a modeless Qt WebEngine window with a native evidence table and selection bridge.

**Tech Stack:** Python 3.11+, existing PySide6 6.11.2, MapLibre GL JS, PMTiles JavaScript reader, Protomaps-compatible basemap assets, unittest, PyInstaller.

**Spec:** `docs/superpowers/specs/2026-10-16-survey-mapping-design.md` (approved).

## Global Constraints

- Qualified positions: available coordinates, age 0–10,000 ms, horizontal accuracy 0–25 m, no true mock flag; recompute using `qualify_location`.
- Longitude precedes latitude; preserve genuine zero coordinates; never invent missing coordinates.
- First qualified fix represents each run; retain all observations and unpositioned runs.
- No automatic network access, GPS acquisition, uploads, geocoding, or basemap downloads.
- Keep evidence immutable; preferences contain map-pack paths, evidence does not.
- Bundle renderer, styles, fonts, sprites, attribution, and licenses; no external CDN dependencies.
- WebEngine/WebGL failures preserve a usable native point list and diagnostics.
- Support Windows and Linux; state platform verification accurately.
- No heatmaps, interpolated coverage, tracks, tower inference, or cellular/SDR metric coloring in this increment.

## Review Focus

1. Legacy/malformed evidence must leave other survey runs viewable (Task 1).
2. Duplicate observation identifiers across runs and overlapping coordinates must remain individually selectable (Tasks 1, 3).
3. Selected pack deletion/replacement, truncated ranges, and incompatible schemas must produce a clear fallback (Tasks 2, 3).
4. Antimeridian and polar evidence must retain original coordinates and sensible map framing (Tasks 1, 3).
5. Script-like labels, unauthorized bridge IDs, external requests, and frozen helper failures must not execute content or break diagnostics (Tasks 2–4).

## Task 1: Derived GPS evidence model

**Files:** Create `src/veilbreaker/map_data.py`, `tests/test_map_data.py`; use existing `location_report.py`, `android_capture.py`, and saved run records.

**Interfaces:** `build_map_data(runs: list[dict]) -> dict`, where each run supplies `run_id`, `label`, and `locations` (existing location rows). Result: `features` GeoJSON FeatureCollection, `rows` native table records, `representatives` feature IDs, `counts`, and `warnings`. IDs are generated opaque stable indices within this model, independent of user-provided IDs. `map_bounds(features: list[dict]) -> list | None` returns antimeridian-aware west/south/east/north bounds. `export_geojson(model: dict, feature_ids: list[str]) -> str` exports exactly the selected view with standards-compliant finite JSON.

- [ ] Write tests for coordinate order/zero, invalid/nonfinite/missing values, 10,000/10,001 ms, 25/26 m, mock, stale stored quality, first-qualified representative, and legacy empty rows. Assert invalid evidence creates warnings/unpositioned rows without losing other runs.
- [ ] Add tests for duplicate observation IDs across runs, overlapping points, ±179° bounds spanning 2°, and polar evidence retained in rows/export but excluded from Web Mercator rendering (limit 85.05112878°). Assert no input mutation or whole-run signal copying.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p test_map_data.py`; confirm missing-module failure.
- [ ] Implement interfaces with quality recomputation and a separate renderable flag. Include raw location metadata, run/observation identity, and quality reasons in feature properties. Create uncertainty polygons only for a selected valid accuracy-bearing point, with a display limit and explicit message for impractically large uncertainty; never alter evidence accuracy.
- [ ] Run the same tests; require all passing. Commit this task.

## Task 2: Offline assets and restricted map service

**Files:** Create `src/veilbreaker/map_server.py`, `src/veilbreaker/map_pack.py`, `src/veilbreaker/assets/maps/`, `tools/vendor_map_assets.py`, `tests/test_map_server.py`, `tests/test_map_pack.py`.

**Interfaces:** `inspect_pack(path: Path) -> dict` returns validated v3 header information, size, schema compatibility, and attribution. `MapServer(asset_root: Path)` exposes `start() -> str`, `set_pack(path: Path | None) -> dict`, `set_model(model: dict) -> None`, and `close() -> None`. The returned URL contains a random per-instance token. Endpoints are explicit registrations for assets, model JSON, and selected pack bytes only.

- [ ] Write HTTP tests for GET/HEAD, valid inclusive/open/suffix ranges, invalid/multiple/oversized ranges, missing token, traversal, unregistered resources, unexpected Host/Origin, denied mutation methods, and shutdown. Bound each pack response to 16 MiB and reject larger requests with a clear client error.
- [ ] Write pack tests for bad magic/version, out-of-file offsets, truncated header/metadata, unsupported tile/schema/compression, deleted/replaced selected file, and excessive decompressed metadata (1 MiB cap). Support Protomaps-compatible vector PMTiles only initially; explain other schema rejection.
- [ ] Run both new test files and confirm expected failures.
- [ ] Inspect current official upstream releases; choose compatible exact versions and record source URLs, hashes, and licenses in `assets/maps/manifest.json`. Vendor JavaScript/CSS and the matching Protomaps style, sprites, and font assets with the reproducible tool. Bundle assets rather than fetching them at runtime.
- [ ] Implement bounded file streaming and pack validation, loopback binding, resource allowlisting, no directory listings, no CORS wildcard, and CSP limited to local assets plus required MapLibre workers. Detect pack replacement instead of mixing old metadata with new bytes. Close open handles/server threads on shutdown.
- [ ] Run both test files; require all passing. Commit this task.

## Task 3: Map window and existing workflow integration

**Files:** Create `src/veilbreaker/map_ui.py`, `src/veilbreaker/assets/maps/index.html`, `src/veilbreaker/assets/maps/app.js`, `tests/test_map_ui.py`; modify `gui.py` and `survey_ui.py` at result/survey actions, selected run loading, and application shutdown. Add a small `map_sources.py` adapter and corresponding tests rather than expanding core acquisition code.

**Interfaces:** `load_run_map_data(config, run_id: str) -> dict` reads stored normalized location rows, falling back to validated bounded Android evidence for older records. `load_survey_map_data(config, survey_path: Path) -> dict` gathers active survey runs without acquiring data. `MapWindow(parent, model: dict, open_run: Callable[[str], None])` owns its service and emits/calls only allowlisted run IDs. Qt bridge `selectFeature(feature_id: str)` selects known model IDs; renderer-ready/error events update native status.

- [ ] Write adapter tests for mixed old/new runs, missing evidence, tombstoned runs, and malformed one-run data without hiding valid neighbors.
- [ ] Write UI tests for empty evidence, overview representatives versus per-run observations, initially hidden questionable fixes, overlapping-point list selection, map/list synchronization, unknown bridge IDs, escaped labels, and export matching visible filters.
- [ ] Add failure tests for missing WebEngine, renderer timeout/error, deleted pack, denied external navigation/popups, and shutdown cleanup. Keep native table and Open diagnostic functional in each failure case.
- [ ] Run adapter/UI tests and confirm expected failures.
- [ ] Implement modeless dark teal map window with Fit measurements, Import offline map, Show questionable fixes, run/observation selection, GeoJSON export, native details, and counts with explicit units. Keep basemap attribution visible and preferences separate from evidence.
- [ ] Implement bundled MapLibre page using JSON transfer and DOM text APIs, no interpolated HTML. Use a blank coordinate view when no compatible pack exists, labelled “Basemap unavailable”. Block external URLs at the WebEngine request/navigation layers; allow only owned local resources and necessary internal worker schemes. Register Qt bridge solely for trusted application content.
- [ ] Integrate Map actions in diagnostic results and survey details. Resolve Open diagnostic through existing record-loading code. Retain owned windows until closed; stop all services on application exit. No acquisition actions are triggered by opening a map.
- [ ] Run tests and source GUI smoke with synthetic points, a compatible licensed test pack, and offline networking. Check clicks, uncertainty, ±179° framing, polar explanation, and resize behavior. Commit this task.

## Task 4: Frozen packaging and delivery

**Files:** Modify `Veilbreaker.spec`, `pyproject.toml` package-data patterns, `tools/build_release.py`, version metadata, and release documentation; create `tools/map_smoke.py` and a tiny attributed PMTiles test fixture.

**Interfaces:** Map smoke emits JSON containing renderer readiness, rendered feature count, selection round-trip, local pack request success, and external request denial. Build fails if any required map smoke assertion fails; native-only fallback is tested separately, not counted as successful map rendering.

- [ ] Add source/frozen smoke assertions before enabling packaging; confirm current package cannot pass because WebEngine is excluded.
- [ ] Include WebEngine/QtWebChannel imports, subprocess executable, resources/locales, and recursive map assets. Make tests usable on Linux as well as Windows; avoid platform-specific absolute paths.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests`, then `tools/map_smoke.py` in source mode. Require all checks passing and visually inspect a map screenshot.
- [ ] Use the requesting-code-review skill for one fresh review of the completed branch under native execution; resolve important findings and rerun affected checks.
- [ ] Run `.venv/Scripts/python.exe tools/build_release.py` with frozen map smoke included; require verified manifest. Run `./build-installer.ps1 -SkipBuild`; verify installer exists and hash is generated. Run Linux build/smoke if a suitable environment is available; otherwise explicitly record it as unverified.
- [ ] Update release notes with included features, optional map-pack requirement, installer size change, and remaining field-validation limitations. Commit and push completed work using existing authorization; provide installer and concise verification results.

## Execution recommendation

Native execution: implement these four dependent tasks in the current session, followed by one independent review. This keeps interface coordination and context overhead low. Plan awaits user review before implementation.
