# Cell-reference matching and regional terrain assessment

Date: 2026-10-20. Status: proposed implementation design for review.

## Intent

Extend the existing offline field-survey workflow: inspect a captured serving cell,
find a matching reference location, view receiver-to-reference distance/bearing,
and assess a selected path against terrain. Preserve useful diagnostics with
missing data, limited equipment, and no network connection. Receiver GPS, estimated
cell positions, operator-entered sites and verified physical structures remain
separate evidence classes. No nearest-tower or PCI-only identification.

## Approach and alternatives

Recommended: staged local data adapters, starting with an indexed cell database,
then regional elevation data and explicit path assessments. Online per-test lookup
would require credentials/connectivity and make repeatability harder. Bundling a
national tower/elevation archive would increase installer size and update costs.
Neither is required. Bulk data stays separate from application binaries and Git.

### Phase A — useful serving-cell matching

Add **Cell references** to map tools: import an authorized OpenCellID full country
CSV/CSV.GZ, inspect source/date/license/row counts, activate an imported snapshot,
and remove a registration without deleting exported evidence. Initial support is
LTE; other technologies are counted as unsupported, not silently relabelled. NR
remains unresolved until the source schema and identity semantics are validated.
Support a small Veilbreaker JSON import for operator-entered LTE/NR sites with
explicit full identity, coordinates, provenance and verification status. Operator
records are labelled as such; entering a record is not automatic verification.

Stream imports in a cancellable worker to a new SQLite database. Index
(radio, MCC, MNC, TAC, full cell ID); preserve source row, coordinate estimate,
sample count, created/updated timestamps and provider range without interpreting
range as certified positional accuracy. Validate finite coordinates, identity
ranges and timestamps; report rejected/unsupported rows. Reject malformed headers,
daily-diff files, empty accepted datasets and corrupt compressed streams. Bound
row length, decompressed bytes, record count and staging disk usage; show progress
and let the user cancel. Activate only after successful validation/commit, leaving
the prior dataset intact on error. Record file SHA-256 and adapter/schema version.
Exact repeated imports can reuse an existing validated snapshot.

For OpenCellID LTE, map net to MNC, area to TAC, cell to full ECI. Preserve original
values alongside normalized numeric lookup keys; keep radio namespaces separate.
Do not split cell ID to infer an eNB/gNB or infer MNC from a carrier name. Duplicate
identities with different locations remain conflicting candidates. Do not choose
one by proximity, timestamp, or sample count without showing the conflict.

Read explicitly registered cells from the original Android capture observations,
not the aggregated report identity (which may combine later non-null fields).
Retain observation/subscription/cell indices. Match identity independently of GPS;
only compute receiver distance/bearing from qualified GPS in the same observation.
Expose modem/GPS age and time offset. A survey's first GPS fix must not silently
be assigned to a cell observed elsewhere later in the capture.

Result states: reference match, conflicting references, not found, incomplete
identity, unsupported technology, reference unavailable. A reference match means
identity matched, not physical tower verified. No reference data is not a failed
network diagnostic. Neighbor cells remain reference observations, not serving cells.

Map selected matches and receiver points using different symbols; connect them
with **bearing to reference**, never **LOS**. Selection shows observed network,
band and RSRP/RSRQ/SINR where exposed, full identity, reference provenance/date and
distance/bearing when qualified. Limit the first view to the selected run/observation
and matched candidates rather than plotting millions of nationwide records.

Save explicitly generated match context as derived survey/run attachments. Reports
embed selected records and attribution, dataset hash, matching version and capture
identity; exports remain reproducible after reference replacement/removal. Keep
original diagnostic bundles unchanged. Missing/stale attachments produce a readable
status rather than broken reports. Existing report imagery stays independent.

### Phase B — regional terrain and LOS

Add **Assess path** on a selected candidate or operator-entered site. An ambiguous
identity requires selecting a candidate explicitly; results retain its uncertainty.
Manual site coordinates do not establish that the receiver connected to that site.

Use local regional GeoTIFF/COG DEM imports (USGS 3DEP first). A rasterio/PROJ adapter
reads georeferencing and samples in the raster CRS; do not hand-decode arbitrary
TIFF or assume degrees/meters. Keep this adapter isolated from the matching engine.
Before packaging it, verify Windows frozen dependency loading and source Linux
availability. Read local files only; remote raster paths and embedded remote
references are not an implicit download mechanism. Initial qualified terrain
support requires known horizontal CRS, elevation units and vertical datum, with
missing metadata confirmed explicitly from source documentation.

Request receiver and destination antenna heights in meters above local ground;
do not substitute phone ellipsoid altitude, mast height or a guessed cellular
antenna height. Sample a geodesic path including endpoints and all covered raster
segments. Bound distance to 100 km and profile samples to 4096 initially. Respect
raster resolution; if the sample cap would undersample, report insufficient
resolution instead of claiming clearance. No-data, missing tile coverage or mixed
unreconciled datums produces incomplete/unknown assessment.

Display a terrain profile with antenna endpoints and straight-line path. Calculate
terrain-only geometric clearance with explicit effective-Earth-radius factor
(default 1 for geometric assessment; selectable 4/3 refraction assumption). Record
factor, Earth model, spacing/resolution and elevation source/hash. Add frequency-
dependent first-Fresnel-zone clearance when a positive frequency is supplied;
report the selected frequency and 60% clearance criterion. Do not guess a center
frequency from a wide band. Missing frequency leaves Fresnel assessment unknown
while permitting geometric terrain assessment.

Use result labels: sampled terrain obstructed, no sampled terrain obstruction,
incomplete inputs/coverage. Report minimum clearance and obstruction distance;
explain that terrain sampling omits buildings, vegetation and sub-pixel obstacles.
Uncertain cell coordinates make the assessment conditional on that endpoint.
No guaranteed connectivity, coverage prediction or optical visibility claim.

Cache each explicit assessment with endpoint coordinates/heights, selected reference,
frequency, DEM identity, sampling/model assumptions and calculation version. Embed
profile PNG/table and numeric samples in native/portable reports and evidence ZIPs.
No raster access or online fetch is required to reopen an exported assessment.

## Integration boundaries

New modules: cell_reference_store/import, cell_matching, cell_reference_ui,
terrain_raster, terrain_profile, path_assessment_ui/report. Reuse bounded Qt workers
with explicit QObject slots and wait for cancellation before closing dialogs.
Reuse survey attachment/export patterns without rewriting captured evidence.
Matching can ship and work without the terrain adapter installed or configured.
Automated OpenCellID downloads, API-token storage, FCC ASR association, national
DEM preparation and building-aware propagation are outside this increment.

## Verification and delivery gates

- Synthetic CSV/GZIP fixtures: valid imports, numeric boundaries, duplicate/conflict
  identities, bad rows/header, truncated gzip, size limits, cancellation, replacement.
- Matching: exact LTE key, leading-zero representation, wrong TAC/radio/network,
  incomplete identity, PCI-only rejection, NR unresolved, operator provenance.
- Observation alignment: multiple cells, subscriptions and locations; unknown/old
  GPS; stale capture evidence; no combining independent observation identities.
- Offline UI/report/export: matching with/without basemap, attribution, escaped
  labels, saved context integrity, removed reference database, no network access.
- Terrain: synthetic flat/ridge/valley rasters, CRS transforms, unit conversions,
  nodata gaps, endpoints, curvature, frequency/Fresnel analytic fixtures, sample cap.
- Explicitly check numerical results against an independent analytic fixture;
  visually inspect profile and map in the native viewer and frozen Windows build.
- Qualify a small real authorized reference sample and a regional 3DEP tile before
  claiming real-data acceptance. No such user dataset/token is currently supplied.
  Synthetic fixtures prove functionality, not real serving-tower identification.
- Deliver matching first with report integration; then terrain/LOS after numerical
  and native-dependency gates. Build installer, document limitations, commit/push.

## Primary source checks (2026-10-20)

- https://docs.opencellid.org/docs/downloads/database-format — bulk fields and units;
  initial adapter uses documented LTE semantics. Deprecated fields do not imply
  physical verification or current received signal.
- https://docs.opencellid.org/docs/downloads/overview — token-based acquisition,
  country exports and attribution/license; user obtains an authorized dataset.
- https://docs.opencellid.org/docs/help/troubleshooting — complete identity lookup;
  cells and physical sites are distinct.
- https://www.usgs.gov/faqs/what-types-elevation-datasets-are-available-what-formats-do-they-come-and-where-can-i-download
  — regional 3DEP DEM/COG data; confirm each imported product's metadata.
