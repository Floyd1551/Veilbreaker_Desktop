# Regional terrain and structure packs

Open **Configuration → Regional terrain and structure packs**. The **Add / download** tab can copy a local file or download one explicit HTTPS URL. The **Installed packs** tab shows coverage bounds, provider, source date, license/terms, SHA-256, install time and integrity status. Use **Verify SHA-256** after moving or restoring the data directory.

## Huntsville preparation

Choose **Huntsville, AL area**, then **Find USGS terrain for area**. The preset `[-87.2, 34.3, -86.2, 35.2]` is a search box covering Huntsville and nearby areas, not a promise that any one product covers the whole box. Select a result, inspect its provider metadata, and enter the confirmed vertical datum and elevation units before downloading. Install adjacent products separately where necessary. The current path assessment uses one GeoTIFF at a time and reports no-data gaps; it does not stitch adjacent rasters.

The catalog searches the [USGS National Map API](https://tnmaccess.nationalmap.gov/api/v1/docs) for 1/3 arc-second terrain GeoTIFFs. USGS [3DEP information](https://data.usgs.gov/datacatalog/data/USGS%3A3a81321b-c153-416f-98b7-cc8e5f0e17c3) identifies the source dataset. The catalog's product date is kept separate from download/install time. Veilbreaker does not infer a vertical datum or unit from a product title.

For a physical-structure pack, select **Physical structures · GeoJSON** and provide an authorized regional WGS84 Point FeatureCollection. Required properties: `structure_id`; optional: `owner`, `height_agl_m`. Enter the source's declared extent, provider, terms and date. Example:

```json
{"type":"FeatureCollection","features":[{"type":"Feature","geometry":{"type":"Point","coordinates":[-86.59,34.73]},"properties":{"structure_id":"SOURCE-123","owner":"Example","height_agl_m":30}}]}
```

The declared bounds describe the supplied records, not their completeness. A structure is not automatically a cellular transmitter, carrier site or the serving tower. The manager does not currently fetch or translate an FCC tower feed, connect a structure to OpenCellID, or show structure markers on the survey map. Tower records must be supplied as documented GeoJSON from a source the operator may use. Treat `owner` as source metadata, not carrier attribution.

Downloads are bounded, cancellable and installed only after validation. An optional published SHA-256 can be entered; otherwise the app computes one and labels it accordingly. Download URL query parameters are not retained in the manifest. Data files are stored under the app data directory's `regional-packs` folder, separately from the installed program, so they persist across upgrades. Downloads do not resume if interrupted.

For LOS/Fresnel, open a selected cell reference candidate's path assessment and choose **Use installed terrain**. The resulting assessment includes the raster checksum and pack provenance. This is still conditional on the selected reference endpoint, antenna heights and terrain coverage; it is not a proof of serving-cell identity. Bare-earth terrain omits buildings and vegetation.
