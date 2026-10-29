# Veilbreaker field-platform progress checklist

Updated 2026-10-28. This tracks implemented software separately from field qualification and 1.0 readiness. See `V1_FIELD_PLATFORM.md` for the 1.0 acceptance criteria.

## Implemented in the desktop build

- [x] Windows/Linux source and CLI, Windows installer, offline reports, run history and evidence exports.
- [x] Receive-only HackRF capture and Android companion import/live USB input paths.
- [x] Survey sessions, saved runs, manual geographic and multi-floor plan placement, and portable survey assets.
- [x] Offline map foundation, local cell-reference import, and single/multi-raster terrain LOS/Fresnel assessment.
- [x] Searchable offline Tools, multiple calculator/reference tabs, saved input presets and initial RF/network/fiber/PoE tools.
- [x] Explicit FSPL-to-Link-budget calculation handoff with source limitations retained.
- [x] Managed regional single-raster terrain and physical-structure GeoJSON packs; in-app import/download, bounds and provenance, checksum verification, and terrain assessment handoff.
- [x] Cross-tile local terrain sampling with datum/unit checks, per-tile hashes and provenance, and explicit no-data gaps.
- [x] Seven-workspace desktop navigation, explanatory collector cards, Evidence utilities, and separated Configuration/Settings controls.
- [x] Local vector icons for navigation, collector and Tools cards; Veilbreaker emblem in sidebar and Overview.
- [x] Collector readiness snapshot labels in Investigate, with missing and untested states distinct from actual connection claims.
- [x] Geographic survey map metric selector, relative measured-value coloring, legend and run-metric details. Manual/GPS outlines remain distinct; missing values stay uncolored.
- [x] Floor-plan measured-point coloring with per-floor scales, missing-value markers, manual-placement outlines, clickable scan details and persistent saved positions.
- [x] Recorded metric-source filters and capture/phone-receipt timing in geographic and floor-plan survey views; attached phone LTE/NR metrics remain separate from desktop modem readings.
- [x] Read-only survey median for a live Android session with one reported cell group and fresh, uncached samples; receipt window, sample count, identity and source stay visible.
- [x] Optional deployment of the supplied CONUS overview and OpenCellID MCC 311 snapshot, with observed coverage, source attribution, and LTE/NR full-identity lookup.
- [x] Offline area preview for registered map bounds, terrain extent gaps, structure extents and actual cell-reference record counts by radio and network.
- [x] USGS area catalog suggestions for adjacent terrain extents, older-result review and detection of already installed source URLs.
- [x] Optional sparse 121-point terrain no-data preview, with missing examples, overlap fallback and declared datum/unit comparison.

## In progress or limited

- [ ] Complete area preparation with denser or full no-data analysis, verified tower/cell providers and offline imagery packs. The 121-point preview can miss holes between samples.
- [ ] Extend beyond the supplied MCC 311 estimated-cell snapshot with authorized broader cell and physical tower datasets; retain the distinction between sites and serving-cell identity.
- [ ] Expand adjacent-tile preparation to batch downloads and field qualification of real terrain boundaries. Four Huntsville USGS tiles are installed locally; one cross-boundary test sampled 217 points without missing elevations. This is not a full-area no-data or LOS validation.
- [ ] Add per-cell selection/filtering for live Android sessions with several reported groups. These remain separate detailed evidence; current live survey colors are run-level medians, not per-fix samples.
- [ ] Guarded estimated heat-map surfaces, visibly distinct from measured points.
- [ ] Environmental observations and attaching calculation snapshots to surveys, points and reports.
- [ ] Broader offline reference/tool library and field workflows from the approved inventory.
- [ ] Live hardware connection status cards, contextual Evidence actions, and deeper visual polish from the approved UI direction. Readiness labels are prerequisite snapshots only.

## 1.0 release gates

- [ ] Prepare a real survey area in the app, disconnect, then reopen map, terrain, tower candidates and LOS report with provenance intact.
- [ ] Qualify real Android, HackRF and GPS survey workflows plus disconnect/recovery behavior on supported Windows and Linux builds.
- [ ] Verify installer lifecycle, dataset licenses/source dates, offline coverage limits and release documentation.

An implemented path is not a claim that every device, dataset or field condition has been qualified. A calculated or estimated value must remain distinguishable from captured evidence and operator placement.
