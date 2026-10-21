# Regional terrain and LOS implementation plan

> **For agentic workers:** Use superpowers:executing-plans for native execution, or superpowers:subagent-driven-development if the user selects delegation. Implement task-by-task.

**Spec:** ../specs/2026-10-20-tower-matching-terrain-design.md (approved by user).

**Goal:** Assess a selected receiver-to-reference path using local elevation and explicit antenna/frequency assumptions, then retain the result in offline reports.

**Architecture:** Isolate local raster reading from a pure numerical profile engine. Save calculated samples, parameters and derived images as immutable assessment attachments. Depends on the selected candidate and attachment contracts in the cell-reference plan.

**Tech Stack:** Python, PySide6, rasterio/PROJ adapter (versions pinned after compatible-wheel qualification), existing portable HTML and evidence manifest.

## Global constraints

- Maximum path 100 km; maximum 4096 samples including both endpoints.
- Require finite nonnegative antenna heights AGL, declared compatible vertical datum
  and meter/foot elevation units. Never substitute phone altitude for terrain elevation.
- Effective Earth-radius factor defaults to 1; offer 4/3 explicitly. Frequency must
  be positive for Fresnel results. Default required first-zone clearance is 60%.
- Missing terrain/height/datum or insufficient sampling produces incomplete status.
- No connectivity guarantee, building/vegetation model or nationwide elevation bundle.
- No implicit remote raster access; loading a report must require neither DEM nor network.

## Review focus

- Source CRS/axis order and foot-to-meter conversions can create plausible wrong profiles.
- Nodata gaps and endpoint holes must never become zero elevation or clear terrain.
- Candidate location uncertainty must remain visible even for an unobstructed profile.
- Long paths must not silently thin samples below source terrain resolution.
- Frozen native GIS libraries must fail gracefully without breaking cell matching.

### 1. Pure profile calculation

Files: create `src/veilbreaker/terrain_profile.py`, `tests/test_terrain_profile.py`.
Interface: `assess_profile(distances_m, elevations_m, receiver_agl_m,
site_agl_m, frequency_mhz=None, earth_factor=1.0, fresnel_fraction=0.6) -> dict`.
Return geometric minimum clearance, first obstruction distance, Fresnel status and
all assumptions; statuses are sampled-terrain-obstructed, no-sampled-obstruction,
and incomplete. Strictly increasing distances must start at zero and end at D.

- [ ] Tests: flat ground with equal antenna heights, a ridge above the path, a valley,
  missing sample, missing endpoint, negative/NaN heights, zero frequency, duplicate
  distances, 100 km cap, and a midpoint analytic curvature/Fresnel fixture.
- [ ] Observe RED; implement the pure numerical engine with Earth radius 6371008.8 m.
  At distance x, Earth bulge is x(D-x)/(2*k*R). LOS is the linear interpolation of
  endpoint ground+AGL heights. Clearance subtracts terrain plus Earth bulge.
  First Fresnel radius is sqrt((299792458/f_Hz)*x*(D-x)/D). Exclude endpoints from
  Fresnel obstruction classification; keep them in numeric output.
- [ ] Verify analytic expected values independently and test missing-frequency behavior;
  run focused tests GREEN; commit.

### 2. Regional DEM adapter and sampling

Files: create `src/veilbreaker/terrain_raster.py`, `tests/test_terrain_raster.py`;
modify `pyproject.toml`, `veilbreaker.spec` only after compatibility checks.
Interfaces: `inspect_dem(path, declared_metadata) -> dict`,
`sample_path(path, start_lonlat, end_lonlat, declared_metadata, cancelled) -> dict`.
Metadata includes source, horizontal CRS, vertical datum, units, nodata, resolution,
checksum and operator-confirmed fields. Start/end coordinates come from selected
qualified GPS and reference; estimated/manual site status travels with them.

- [ ] Confirm compatible rasterio/PROJ Windows wheels and Linux support from official
  documentation; pin the tested dependency versions. Keep GIS imports lazy so the
  matching UI can explain unavailable terrain support without aborting.
- [ ] Write synthetic GeoTIFF tests for geographic/projected CRS, meters/feet,
  rotated geotransforms, nodata, no CRS, missing units/datum, out-of-extent endpoints,
  cancellation, external sidecars/references and resolution exceeding the sample cap.
- [ ] Observe RED; allow local single-band GeoTIFF only, inspect driver and georeferencing,
  reject URL/VSI paths and unapproved external resource dependencies. Bound reads via
  raster windows, not full nationwide raster arrays. Sample a geodesic with PROJ,
  transform always-xy into raster CRS and preserve nodata. Use nearest cell sampling
  with explicit resolution limits; do not claim detection of sub-pixel obstacles.
- [ ] Reject incomplete coverage instead of silently joining mismatched datums.
  Verify focused tests GREEN and a small real regional DEM when available; commit.

### 3. Path workflow and readable profiles

Files: create `src/veilbreaker/path_assessment_ui.py`, `path_assessment_report.py`,
`tests/test_path_assessment_ui.py`; modify cell reference/map dialogs.
Interface: `PathAssessmentDialog(parent, config, selected_endpoint_context)`.
Result context includes endpoint provenance, DEM metadata, numerical samples and
an embedded PNG profile rendered with Qt; plot generation is separated from raster work.

- [ ] Write tests for explicit candidate selection, unknown heights, cancelled worker,
  missing GIS runtime, unsupported datum, missing frequency and report escaping.
- [ ] Observe RED; add **Assess path** with DEM selection, metadata confirmation,
  receiver/site AGL heights, optional frequency and geometric/refraction selector.
  Worker cancellation follows explicit bound-slot lifecycle used in imagery.
- [ ] Render terrain, LOS and optional 60% Fresnel lower envelope with labeled axes,
  endpoint heights, minimum clearance, obstruction position and source assumptions.
  Unknown inputs retain an actionable explanation instead of a green clearance badge.
- [ ] Verify GUI tests, native profile screenshots and numerical annotation consistency;
  commit.

### 4. Saved assessments, export and installer qualification

Files: create `src/veilbreaker/path_assessment_store.py`, `tests/test_path_assessment_store.py`;
modify survey report/export hooks, release docs and build configuration.
Interfaces: `save_assessment(config, survey_path, assessment) -> dict`,
`load_assessments(config, survey_path) -> list[dict]`. Save bounded immutable JSON/PNG
under survey assets with hashes; retain DEM identity, selected reference, positions,
heights/frequency/model and calculation version. Reports never recalculate on open.

- [ ] Tests: previous result survives failed save, corrupt/missing asset warning,
  changed inputs flagged stale, report opens without DEM or reference database,
  assessment JSON/PNG included and verified by exported evidence manifest.
- [ ] Observe RED; implement storage and same native/portable report section, then GREEN.
- [ ] Independent review of numerical logic, input qualification and GIS deployment.
- [ ] Run full suite, native profile inspection and frozen adapter tests with a synthetic
  raster. Build installer only after native dependency loading passes. Document real-data
  validation separately; no field validation claim without a real surveyed endpoint.
- [ ] Commit/push verified release and record installer checksum.


## Execution status — October 21

Implementation and source checks completed; see `docs/cell-terrain-execution.md`
for task results and explicit scope rulings. Release qualification passed 226 tests
and the frozen GIS smoke. Final GUI/map and installer qualification are recorded
in the release notes when complete. Real serving-tower field validation remains
pending an authorized dataset and surveyed endpoint/antenna heights.
