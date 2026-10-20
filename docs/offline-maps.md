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


## Saved map catalog and report imagery (0.36)

Imported maps appear in the saved-map selector with size, zoom range and source
date when known. Select **Use selected map** to switch. **Remove registration**
only removes the list entry; it never deletes the archive. The prepared CONUS
zoom 0–10 overview is a separate approximately 379 MiB file, not installer content.

In **Site Surveys**, open a survey and choose **Prepare report map…**:

1. Review the proposed area around the first qualified GPS fix for each test.
   Without qualified GPS, enter an area manually; the report labels that fact.
2. Choose **Download USGS aerial preview** while online, or import an offline
   PNG/JPEG and its georeferencing JSON. Only the selected bounds are sent to USGS.
3. Review coverage and numbered markers, then **Save map to survey**.
4. Open the survey report or export its evidence. Both contain the annotated image,
   source, attribution, acquisition date when known, preparation time, point legend,
   north arrow and approximate scale. No download occurs during viewing/export.

USGS NAIP is aerial photography, not a live satellite feed. The service may not
provide an acquisition date for the returned mosaic; **Unknown** is intentional.
The copyright/service date is not treated as image acquisition time. Provider
availability and coverage can vary. A failed or cancelled preparation preserves
the previous saved image. Without an image, normal survey reports still work.

Adding tests or changing qualified positions marks the saved overlay out of date.
Use **Regenerate from saved image** when the existing image covers all points;
otherwise prepare a larger area. Old exported reports remain unchanged. Restoring
a recoverably deleted survey retains its imagery. Tower identity and terrain/LOS
analysis are not inferred from these photographs.

### Offline imagery sidecar

Use a north-up, unrotated PNG/JPEG (maximum 2048 pixels per side and 20 MiB) with a
same-named `.json` file, or select the sidecar separately. Bounds describe the
outer image edges in the stated CRS. EPSG:4326 uses longitude/latitude degrees;
EPSG:3857 uses Web Mercator meters. Example:

```json
{
  "schema_version": 1,
  "crs": "EPSG:4326",
  "bounds": [-96.81, 32.77, -96.79, 32.79],
  "source": "Your imagery provider",
  "attribution": "Provider credit and required attribution",
  "imagery_date": null,
  "imagery_type": "aerial"
}
```

Other supported type labels are `satellite`, `reference` and `vector`; use the
accurate label. Unreferenced photos and GeoTIFF imports are not supported here.
Source imagery, annotated PNG and metadata are stored under the application data
`survey-assets` directory. New survey evidence ZIPs include these assets in their
hash manifest; the HTML also embeds the image so it remains portable on its own.
