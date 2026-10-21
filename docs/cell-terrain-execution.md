# Cell matching and terrain execution record

Approved spec and both implementation plans: 2026-10-20. Native execution.

Ruling: use the existing dedicated checkout on codex/cell-terrain, preserving its
configured Python and native packaging tools; no parallel implementation workers.
Task 1 started: bounded reference import and immutable SQLite snapshots.


Tasks 1–2: reference and matching RED/GREEN passed; commit 907706d.
Matching UI, derived context/report export and terrain implementation integrated.
Ruling: share cell_context storage for assessments, keeping numeric samples and
base64 PNG together with provenance; ZIP also receives separate profile PNGs.
This avoids two independent pointers drifting out of sync. Cost: an assessment
is saved together with selected cell context rather than as a separate document.
Ruling: retain explicit dataset deactivation rather than deleting reference archives.
No reference or captured data is silently removed.
Ruling: deliver one integrated 0.37 release after validating both independent engines,
reducing duplicate installer builds. Matching retains lazy terrain imports.
Ruling: bound matching output to 200 observations and 200 candidates per run, with
explicit omitted/limit statuses. A broad capture can be viewed without unbounded UI data.
Ruling: regional DEM adapter initially reads one self-contained GeoTIFF up to 8 GiB;
paths crossing multiple files require a prepared regional mosaic. Gaps stay incomplete.
Review fixes: closing parent map/main window defers while any new background worker
runs; matching pins dataset UUID for the entire operation. Both observed RED then GREEN.
Projected raster with no nodata exposed scalar mask indexing; corrected with NumPy
getmaskarray and verified EPSG:3857 sampling. Analytical curvature/Fresnel fixtures pass.
Real-data adapter check: a 256x256 USGS 3DEP float32 Dallas regional export yielded 258
samples without gaps. Datum was declared from CONUS source documentation; this is
adapter validation, not verified tower/antenna or field LOS validation.

Final raster review: scale/offset regression observed RED; sampling now applies
GeoTIFF band scale and offset before unit conversion. Map filter changes clear
the selected bearing overlay so a previous selection cannot masquerade as a new run.

Release qualification: 226 tests passed; frozen CLI/worker/GUI/map/terrain checks
passed. Native CONUS candidate/bearing rendering and filter reset passed. The
independent reviewer reported two actionable issues, both fixed with regressions;
its follow-up review was unavailable due to the reviewer service usage limit.

Final external-mask test observed RED: disabling GDAL sidecar discovery could
ignore a separate mask. Explicit sidecar detection now rejects such inputs before
opening the raster; regression GREEN. Rebuilt release to include this correction.
