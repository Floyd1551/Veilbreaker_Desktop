# Veilbreaker field-platform progress checklist

Updated 2026-10-27. This tracks implemented software separately from field qualification and 1.0 readiness. See `V1_FIELD_PLATFORM.md` for the 1.0 acceptance criteria.

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

## In progress or limited

- [ ] Complete area preparation with coverage gap preview, verified tower/cell providers and offline imagery packs. The manager handles one terrain raster or one structure GeoJSON per pack; assessments can use several compatible terrain packs.
- [ ] Authorized real tower and cell datasets, with physical structures distinct from estimated cell sites and serving-cell identity.
- [ ] Automated adjacent-tile catalog preparation and field qualification of real terrain boundaries. The local sampler handles compatible installed tiles and missing data.
- [ ] Survey measured-point metric colors, legends, identity/source filtering and detail cards across geographic and floor-plan views.
- [ ] Guarded estimated heat-map surfaces, visibly distinct from measured points.
- [ ] Environmental observations and attaching calculation snapshots to surveys, points and reports.
- [ ] Broader offline reference/tool library and field workflows from the approved inventory.
- [ ] Live hardware status cards, contextual Evidence actions, and deeper visual polish from the approved UI direction.

## 1.0 release gates

- [ ] Prepare a real survey area in the app, disconnect, then reopen map, terrain, tower candidates and LOS report with provenance intact.
- [ ] Qualify real Android, HackRF and GPS survey workflows plus disconnect/recovery behavior on supported Windows and Linux builds.
- [ ] Verify installer lifecycle, dataset licenses/source dates, offline coverage limits and release documentation.

An implemented path is not a claim that every device, dataset or field condition has been qualified. A calculated or estimated value must remain distinguishable from captured evidence and operator placement.
