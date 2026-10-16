# GPS survey mapping — first desktop increment

## Purpose and scope

Veilbreaker is a standalone field diagnostic application. Users need to see where measurements were taken, inspect the supporting GPS quality, and open the associated diagnostic without leaving the application. The user approved MapLibre, offline PMTiles basemaps, and local survey storage as the direction.

This increment adds maps to an individual diagnostic and an existing site survey. It consumes saved GPS evidence; it does not depend on completing reusable phone connections across survey points. Existing collection and reporting continue to work without a map pack or working graphics acceleration.

## Selected architecture

Use MapLibre GL JS embedded in PySide6 QWebEngineView. Bundle pinned JavaScript, CSS, styles, fonts, sprites, and their licenses with the installer. The current PyInstaller spec explicitly excludes WebEngine; packaging must include its helper executable and resources and verify the frozen application.

Use a user-selected regional PMTiles archive as the basemap. Store the selected pack path in application preferences, never in evidence records. Ship the map renderer and styling assets, not a country-sized basemap. An import action validates a pack and explains its source attribution and disk size. A missing or incompatible pack produces an actionable message and a coordinate-only map with an explicit "Basemap unavailable" label. It must not silently contact a public tile server.

Expose bundled assets and the selected pack through a read-only, loopback-only local service with an unguessable per-process URL prefix. Support bounded byte ranges for PMTiles; expose only registered resources, never arbitrary filesystem paths or directory listings. Restrict the embedded page to those resources, disallow remote navigation and new windows, and keep measurement data local. Shut down the service when the application exits.

Keep survey/run records as the source of truth. Build a derived GeoJSON model from saved evidence; no parallel database or cloud backend is necessary for this increment. A narrowly scoped Qt bridge sends point selection back to Python using known run/observation identifiers, not executable text or filesystem paths supplied by the page.

Alternatives considered: an online-first tile service introduces connectivity and provider requirements during fieldwork; a custom Qt painter avoids WebEngine size but would require building map behavior ourselves. The selected design follows the approved MapLibre direction and keeps the renderer reusable.

## Evidence model

Each feature carries run ID, survey point label when present, observation ID, receipt/fix timestamps, coordinates, source/provider, accuracy, age, mock state, and derived quality. Longitude precedes latitude in GeoJSON. Reject nonfinite/out-of-range coordinates; do not substitute zero for missing values. Preserve genuine zero coordinates.

Reuse location_report.qualify_location: qualified positions require available coordinates, nonnegative age at most 10,000 ms, horizontal accuracy at most 25 m, and no true mock flag. Recompute quality from evidence instead of trusting a stored display label. The first qualified fix represents a run in survey overview. Users can inspect all coordinate-bearing observations for that run; runs with no qualified fix remain listed as unpositioned. Questionable fixes are a separate, initially hidden layer and never silently qualify a run.

Accuracy circles describe reported horizontal uncertainty in meters. Positions identify receivers, not tower coordinates. Do not connect points from different runs or infer a continuous track, coverage surface, or tower position.

The first increment colors points by GPS quality. Cellular signal coloring requires exact observation/cell association and will follow separately; whole-run metrics must not be attached to every GPS fix. SDR samples likewise need explicit time association before spatial coloring.

## User workflow

Add a Map action to diagnostic results and survey details. Open a modeless map window inside Veilbreaker using the dark teal application style. Controls: Fit measurements, Import offline map, Show questionable fixes, and point list. Display counts of mapped, questionable, and unpositioned observations/runs.

Selecting a list item or map point highlights both and shows readable coordinates, source, accuracy, freshness, timestamp, and quality reason. Overlapping points remain individually selectable through the list. An Open diagnostic action uses the existing run-loading workflow. Empty evidence produces a clear explanation rather than an empty unexplained canvas.

Allow GeoJSON export of the displayed evidence with identifiers and quality metadata. Existing HTML reports and evidence exports remain usable without WebEngine. Map rendering never modifies or reinterprets original measurement files.

## Failure handling and platform requirements

Missing WebEngine or failed WebGL initialization keeps the point table and diagnostics available and shows a map-specific error. Windows and Linux must be supported; test the installed/frozen WebEngine resources separately from source execution. Handle antimeridian-spanning data without fitting almost the entire world unnecessarily. Polar points outside Web Mercator's latitude extent remain in the evidence table with an explanation; never change stored coordinates to make them render.

Do not request GPS permissions, start acquisition, download maps, geocode coordinates, or upload data merely by opening the map. Basemap provenance and required attribution remain visible when a pack is loaded.

## Verification and delivery

Test valid zero coordinates, missing/stale/mock/inaccurate fixes, legacy evidence without GPS, malformed evidence, duplicate/overlapping locations, antimeridian bounds, polar locations, and run-to-observation association. Test GeoJSON round trips and text injection handling. Test local service range bounds, resource allowlisting, shutdown, and rejection of traversal/unregistered paths.

Perform a source GUI check with synthetic GPS fixtures, then a frozen Windows smoke test proving MapLibre initializes, points render, selection reaches Python, and local pack data can be read. Record Linux verification separately; do not claim Linux packaging passed without a Linux build. Produce a Windows installer after release checks and commit/push the completed increment.

Deferred: automatic regional downloads, satellite imagery, maps on Android, live tracks, signal heatmaps, USB GNSS drivers, cloud synchronization, and reusable survey phone connections. These remain compatible follow-up work.
