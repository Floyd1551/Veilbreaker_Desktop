# Veilbreaker 0.37.0rc1 — cell references and terrain paths

- Import bounded offline OpenCellID LTE snapshots or operator LTE/NR references.
- Match exact identities from original Android observations, retaining conflicts,
  provenance, same-observation GPS quality and observed cellular measurements.
- Show receiver-to-reference bearing on the offline map; no nearest-tower inference.
- Calculate conditional terrain/LOS and 60% Fresnel clearance from local regional
  GeoTIFFs with explicit antenna heights, frequency, vertical datum and Earth model.
- Retain context, numeric profiles and images in offline native/HTML survey reports
  and new evidence ZIPs without rewriting original diagnostic evidence.
- Cancel background imports safely when the map or main application closes.

See [workflow and input requirements](cell-references-and-terrain.md). Real tower
matching needs an authorized reference dataset; the installer includes no tower
inventory. Terrain modelling excludes buildings and vegetation and does not predict
connectivity. Linux packaging and a real surveyed-endpoint field trial are not
claimed verified by this Windows release.

Validation includes exact matching, conflict/cancellation cases, dataset pinning,
parent-window shutdown, snapshot integrity and portable exports; analytic curvature
and Fresnel fixtures; geographic/projected rasters, nodata, units and scale/offset;
native profile rendering and a small real USGS 3DEP adapter sample. Release build
checks additionally exercise the frozen GIS raster/projection/profile path.


226 source tests passed. The frozen CLI successfully read a synthetic GeoTIFF,
transformed coordinates, sampled a blocking ridge, calculated terrain/Fresnel
results, and rendered the profile. An end-to-end synthetic Android capture,
reference match, terrain assessment and survey ZIP passed manifest verification.

Frozen CLI, Unicode worker/evidence, six-page GUI, offline map and terrain smoke
checks passed. Native CONUS rendering also showed both selected receiver/reference
endpoints and their bearing line; changing the run filter clears the overlay.
