# Offline GPS maps

Veilbreaker 0.35 adds **Map GPS evidence** on diagnostic results and **Map survey GPS** in survey details.

The overview selects the first qualified position for each run. Select a run to inspect all its observations. A qualified fix is at most 10 seconds old, reports horizontal accuracy of 25 meters or better, and is not marked mock. Questionable fixes are hidden until enabled. Points are receiver locations, not tower locations. Selecting a point shows its accuracy circle and evidence; **Open diagnostic** returns to the corresponding test.

## Regional basemaps

Choose **Import offline map** and select a Protomaps-compatible version 3 `.pmtiles` archive. The application uses that local file in place; keep it available. Moving/removing it does not remove measurement evidence. Without a pack, points and the evidence table remain available on a coordinate-only view. No map data or scripts are downloaded automatically.

Obtain regional packs from [Protomaps](https://docs.protomaps.com/basemaps/downloads). A full-world archive is very large: use a regional extract instead. The official [PMTiles command-line tool](https://docs.protomaps.com/pmtiles/cli) can extract a bounding box from a current Protomaps build:

```text
pmtiles extract <current-build-url> site.pmtiles --bbox=<west>,<south>,<east>,<north> --maxzoom=14
```

Use the current build URL from the provider; older build URLs expire. This is a preparation step while online. Other PMTiles schemas, raster/satellite archives, and MBTiles are not supported in this first increment. Map source attribution is shown above the map.

**Export GeoJSON** saves the coordinate-bearing evidence in the selected view, including its GPS quality and source. Polar coordinates remain available in the table and export even when outside the map projection. Missing coordinates are never replaced with zero. No interpolated coverage, signal heatmap, or continuous track is implied.

## Packaging and verification

MapLibre, PMTiles, styles, fonts, and icons are bundled locally with license files and an asset hash manifest. Qt WebEngine increases installer size. If WebGL or the embedded renderer cannot initialize, the native evidence table and diagnostic links remain usable.

Development checks cover synthetic captures and a small real Protomaps Dallas extract; these do not substitute for a GPS field trial. Windows source and frozen rendering must pass the release smoke test. Linux source compatibility is retained; Linux packaging is not claimed verified by the Windows release.
