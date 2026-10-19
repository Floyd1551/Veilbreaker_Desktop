# Veilbreaker 0.35.0rc1 — offline GPS maps

Released October 19, 2026.

- Added Map GPS evidence to diagnostic results and Map survey GPS to survey details.
- Added offline Protomaps PMTiles import, GPS quality filtering, reported accuracy circles, point/diagnostic selection, and GeoJSON export.
- Bundled MapLibre, styles, fonts, icons, and required licenses. Regional geographic map packs are imported separately.
- Preserved a native evidence table when WebEngine/WebGL is unavailable. No remote requests are needed to open maps or view evidence.
- Corrected date-line framing, map-pack cache identity, malformed evidence handling, and narrow-window diagnostic action wrapping during review.

## Verification

All 197 regression tests passed. Windows source and frozen smoke checks rendered three synthetic points, selected evidence through a map click, read a local PMTiles archive, blocked an external request, and rendered both points across the international date line. Source rendering was also visually checked against a real, locally extracted Dallas Protomaps basemap. The release build manifest reports all checks passed.

Linux packaging and a physical GPS field trial remain unverified. This release consumes saved GPS evidence; reusable phone survey sessions, continuous tracks, signal heatmaps, and automatic map downloads remain future work.

The Windows portable ZIP grew from approximately 48 MiB to 217 MiB because the embedded Chromium/Qt WebEngine runtime is now included.

## Implementation decisions

Work used a feature branch in the existing clean checkout to retain the configured build runtime; this provides less filesystem isolation than a separate worktree. Native Windows rendering was used for map smoke tests because Qt's offscreen platform lost its graphics context on this host; those tests briefly display a synthetic map window. No review findings were deferred.

See [offline map instructions](offline-maps.md) for regional map preparation and usage.
