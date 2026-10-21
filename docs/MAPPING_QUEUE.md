# CONUS mapping and cell-site reference queue

Prepared October 19; updated October 20, 2026 for the existing 0.35 offline map viewer.
This is a researched delivery queue, not a claim that tower matching or LOS is
implemented. New application components still need their scoped design review.

## Intended outcome

Use equipment already available (phone or USB GPS plus cellular/SDR inputs) to
place field measurements on an offline map, identify a serving-cell location
when reference data supports it, and eventually inspect terrain along the path.
Keep missing data, estimated locations and measured evidence distinguishable.

## Data preparation now

The existing importer accepts Protomaps-compatible vector PMTiles. Prepare a
CONUS-focused overview separately from the application installer and Git source:

- Source: `https://build.protomaps.com/20261019.pmtiles`.
- Bounds: west -125, south 24, east -66, north 50; includes neighboring portions
  of Canada and Mexico. This is a rectangular extract, not a national boundary mask.
- Overview: zoom 0–10; CLI dry-run estimated a 398 MB archive and 418 MB transfer.
- Comparison: zoom 0–12 dry-run estimated a 2.0 GB archive and 2.1 GB transfer.
- These are estimates for this source build; record actual size and SHA-256 after
  extraction. Higher zoom does not add measurement precision to phone GPS.
- Local destination: `map-packs/CONUS-overview-20261019.pmtiles` (Git-ignored).
- Retain attribution, source date, bounds and extraction parameters beside it.

Preparation completed: 397,797,108 bytes; SHA-256
`a22261276f3818ece79bccc9542f15c4d222b4d3dcede98257ab607a34fd7376`.
PMTiles structural verification and the Veilbreaker map smoke test passed with
this real pack, including local tile reads, point selection and blocked external
requests. Provenance and checksum sidecars are in `map-packs/`.

Recommended balance: nationwide overview first, detailed survey-region packs
second. A single high-detail national pack increases download/update cost;
online-only tiles do not meet the field requirement. No size promise is made for
future regional or national builds.

## Delivery order

| Priority | Component | Deliverable and completion evidence |
| --- | --- | --- |
| 1 | CONUS map and pack management | Import and render the prepared overview offline. Then add an in-app list of available packs, coverage, detail level, size, source date, active selection and missing-file recovery. Preserve evidence when a pack is removed. |
| 1a | Survey-area imagery in reports | Prepare/cache a small georeferenced aerial image for the survey area; overlay numbered measurement points and embed it in native/portable survey reports. Retain imagery source, acquisition date where known, fetch date, bounds and attribution. No network calls when viewing a report. See the October 20 design below. |
| 2 | Local cell reference database | Stream an authorized OpenCellID CSV/CSV.GZ import into indexed SQLite; retain source/license/date, record counts, rejected rows and original reference identifiers. Atomic replacement, cancellation and repeat-import handling. Keep credentials out of reports and Git. |
| 3 | Serving-cell matching | Match radio technology, MCC, MNC, area/TAC and full cell ID using technology-specific rules. Show matching reference records, estimated position, data age and sample count. Never identify the serving site by PCI alone or by choosing the nearest mast. Missing or conflicting identities stay unresolved. |
| 4 | Field map and report overlay | Show receiver position, matched/possible cell locations, distance and bearing, plus the observed carrier/network, band and RSRP/RSRQ/SINR where exposed. Label the connecting line as a bearing, not LOS. Bound viewport queries and cluster dense results. Save reference provenance with exported reports. |
| 5 | Physical structure context | Evaluate FCC ASR as a separate registered-structure layer. Validate its current schema, distribution endpoint and coverage before ingestion. Treat proximity as a candidate association, never an automatic cell-to-mast identity. Structure owner is distinct from network operator. |
| 6 | Regional terrain profiles | Import USGS 3DEP elevation for survey areas; sample a selected receiver-to-site path and plot terrain with explicit endpoint heights and elevation datum. Report missing elevations and uncertain endpoints. |
| 7 | RF path assessment | Add geometric LOS and frequency-dependent Fresnel clearance with stated curvature/refraction assumptions. Distinguish terrain obstruction from missing inputs; do not claim a coverage prediction or guaranteed connection. |

Phases 2–4 provide useful tower context without running a national terrain model.
Use indexed cell-identity lookups and spatial queries, not full-country scans on
every map movement. Import in a background worker; query only the selected run
and visible area. Compute/cache terrain profiles only for selected paths.

## Reference sources and limits

### Basemap

[Protomaps downloads](https://docs.protomaps.com/basemaps/downloads) provide
OpenStreetMap-derived vector archives and support regional extracts. Preserve
OpenStreetMap attribution. Use the [official CLI](https://docs.protomaps.com/pmtiles/cli)
for extraction and its dry-run mode for estimating transfer/storage first.
Provider build URLs have limited retention; a local pack must remain usable after
its original download URL expires.

### Cell identities and estimated positions

[OpenCellID downloads](https://docs.opencellid.org/docs/downloads/overview) are the
first candidate. Country/world exports require an API access token; derived-data
distribution must retain the applicable CC BY-SA attribution/license requirements.
No token or export has been supplied for this task, so acquisition remains pending.

Its [database format](https://wiki.opencellid.org/docs/downloads/database-format)
contains cell identity, estimated coordinates, sample counts and timestamps.
The [provider's guidance](https://docs.opencellid.org/docs/help/troubleshooting)
requires the complete identity, not cell ID alone. Downloads have coverage and
recency limits; absence is not evidence that a cell does not exist. A cell record
is not a surveyed physical tower. Verify actual NR/5G coverage/schema before
claiming NR matching; do not infer a gNB identifier using an assumed bit split.

### Registered structures

FCC's [public-access file documentation](https://wireless.fcc.gov/uls/documentation/pa_intro24.pdf)
lists Antenna Structure Registration downloads. The current FCC web download
pages returned HTTP 403 during this research, so current endpoint/schema validation
is an explicit dependency. Do not promise a complete carrier/cell-ID inventory
from a structure registry. Manual verified-site records should also be supported,
with source and verification status retained separately from imported estimates.

### Elevation and LOS

[USGS 3DEP](https://www.usgs.gov/faqs/what-types-elevation-datasets-are-available-what-formats-do-they-come-and-where-can-i-download)
offers free elevation downloads, including 10 m and 30 m GeoTIFF products. Start
with survey-region coverage. Bare-earth DEMs exclude buildings and vegetation.
LOS needs endpoint antenna heights and compatible vertical datums; phone altitude
and structure height must not silently substitute for these. Show assumptions
and unavailable inputs. Estimated cell coordinates can make an otherwise precise
terrain calculation misleading, so endpoint uncertainty belongs in the result.

## Next implementation slice

Map-pack registration and cached report imagery are implemented in 0.36. Next,
design the local cell database and identity matching together, using imported
files before adding account/download automation. Keep terrain ingestion and LOS
as a later subsystem, with a small regional validation fixture before expansion.

The requested survey-area image is prioritized alongside map preparation, ahead
of tower matching: [map packs and report imagery design](superpowers/specs/2026-10-20-map-packs-report-imagery-design.md).
NAIP is aerial imagery and must be labelled as such; a vector-map snapshot is a
separate fallback, never labelled satellite imagery.


## October 21 implementation update

0.37 implements local LTE/OpenCellID and operator LTE/NR matching plus regional
GeoTIFF terrain assessment. See [workflow and limits](cell-references-and-terrain.md).
FCC structure association, NR bulk-provider validation, automated data acquisition,
multi-file DEM catalogs and building-aware propagation remain later work. A real
cell-reference dataset and surveyed endpoint heights are still needed for field
acceptance; synthetic tests do not identify the user's serving tower.
