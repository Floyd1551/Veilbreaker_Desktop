# Offline data in a release

The prepared Windows build can include the supplied CONUS overview basemap,
OpenCellID MCC 311 country export, and FCC ASR structure snapshot. In a new installation, the included basemap is
selected when no saved map choice exists. Existing map choices and explicit
clearing are respected. Open **Cell references / assess path** from a survey or
diagnostic map to install the included reference into the user's local data and
activate it if no reference choice exists. Existing active or explicitly
deactivated references are respected. These data stay available offline.

The map is a Protomaps vector overview built on 2026-10-19, covering the CONUS
bounding rectangle at zoom levels 0–10. It is not detailed street-level coverage
at every location. Map attribution: © OpenStreetMap contributors,
https://www.openstreetmap.org/copyright. Protomaps describes the basemap as an
ODbL produced work: https://docs.protomaps.com/basemaps/downloads.

The OpenCellID source is the operator-supplied headerless MCC 311 country export.
Its export date was not supplied; the file was modified on 2026-10-27. It does
not cover all U.S. MCCs. Cell locations are community estimates and an identity
match is not a verified physical tower. The build converts supported LTE and NR
records into SQLite and excludes unsupported or invalid rows. Attribution:
OpenCellID, https://opencellid.org, CC BY-SA 4.0,
https://creativecommons.org/licenses/by-sa/4.0/; changes: conversion to SQLite
and filtering. See https://docs.opencellid.org/docs/attribution.

The installed `offline-data/manifest.json` records source and database SHA-256,
map bounds, observed cell-record bounds, technology counts, attribution and
limitations. Observed bounds do not establish complete coverage. The map pack
does not contain terrain, satellite imagery, or a tower inventory; detailed
terrain must be prepared separately. An included FCC snapshot can be
installed from **Regional terrain and structure packs → Install included CONUS
structures**. Existing equivalent, verified packs are reused; other user packs
are preserved.

## Regional terrain and FCC structures

Use the regional pack manager to review suggested USGS terrain tiles and select
up to 20 for sequential download. Confirm the vertical datum and elevation
units against the source before installing. Completed tiles remain available
if a later download fails or the operation is cancelled; a retry skips matching
available sources. Each pack retains its own source, date and checksum.

The pack manager can also import the FCC's complete ASR registration archive
as regional packs or a CONUS collection of bounded physical-structure packs. Download the official
`r_tower.zip` from the link in the importer, enter the archive publication date
and geographic bounds (or select CONUS), and run the import. The archive itself
is not included in the installer. The 2026-10-25 snapshot in the prepared build
contains 139,271 constructed records in 51 populated tiles. CONUS means the
rectangle [-125, 24, -66, 50], which also includes some neighboring areas; it
is not a political boundary or a claim of complete structure coverage. The
import retains its date and SHA-256; filed NAD83 positions
are displayed as approximate WGS84 without a datum transformation. ASR is
incomplete and may be stale: a listed structure is not proof of a serving cell,
carrier, antenna position or current line of sight. Verify the original record
and field conditions before relying on it. On the survey map, select a qualified
recorded location or an operator-placed geographic point, then choose **Nearby
structures / assess path**. Search installed structure packs, explicitly select
a record and review its source before displaying its bearing or assessing the
terrain path. This is an operator-selected physical reference, not an automatic
serving-cell match. Enter actual antenna heights for the path assessment; the
registered structure height is not an antenna height. A survey assessment retains
its receiver and structure provenance; operator placement remains separate from
recorded GPS evidence. Terrain results cover the available terrain data, not
buildings, vegetation, or proof of radio propagation.

Terrain starter windows are available for the 48 contiguous states, with
controls to move the search window. They are small editable search areas, not
state-wide or CONUS-wide elevation coverage. Download and verify the terrain
tiles needed for each area; coverage and no-data gaps remain visible in the
readiness view.

In **Regional terrain and structure packs → Area preview**, optionally select
**Verify intersecting terrain and structure packs** before checking the area.
The background check reports each identified pack's result, source, date,
license, bounds and SHA-256; it can take time for large files. An incomplete
check or failed terrain verification prevents the optional terrain sampling
step. Verification compares file bytes with the locally installed manifest; it
does not establish geographic completeness, data accuracy, or the absence of
no-data gaps. Maps and cell-reference databases are not part of this check.

To check the separate active cell-reference database, select **Verify active
cell reference database** in the same preview. Newly imported snapshots retain
both the original source-file SHA-256 and a separate checksum of the derived
SQLite database. The optional check compares the installed database to that
recorded checksum and withholds cell counts if the database is unverified,
changed or cannot be tied to the same stable reference. Checksums establish
integrity against local metadata, not authenticity, coverage or serving-cell
identity. Older snapshots without a database checksum remain usable as
unverified references. In **Cell references and path assessment**, choose
**Install included cell reference** to copy the checksummed snapshot already
included in a prepared build, or reimport the original source to create a
separate checksummed snapshot. Neither action overwrites or automatically
replaces an active reference. Select the new snapshot explicitly if you wish
to use it.

Area Preview inspects the current header and metadata of registered and included
maps instead of relying solely on saved catalog bounds. Optionally select
**Verify map archive checksums** to compare map bytes against available local
manifest or sidecar checksums. A missing checksum is reported as unavailable,
and mismatched or unreadable maps are excluded from the preview. These checks
do not authenticate the map source, inspect every tile or guarantee network-free
availability (for example, a mapped drive may require a network).

Overlapping structure packs can contain identical records from the same
source, date and terms. Nearby structure search combines identical records
before applying its display limit, preserving alternate pack provenance in the
assessment report. Only the selected pack is reverified immediately before an
assessment; alternate copies are identified as verified at search time.

## Rebuilding with local downloads

Downloaded data is deliberately excluded from Git. Stage these local files:

- `map-packs/CONUS-overview-20261019.pmtiles`
- `map-packs/CONUS-overview-20261019.json` with its `sha256` and source metadata
- `offline-input/311.csv` (headered or headerless OpenCellID export)
- `offline-input/311.json` containing nonempty `source`, `license`, and `date` strings
- `offline-input/fcc-r_tower-20261025.zip`, the FCC registration archive
- `offline-input/fcc-r_tower-20261025.json` with its `sha256` and publication `date`

Set `VEILBREAKER_OFFLINE_DATA_REQUIRED=1` before running `build-installer.ps1`
to fail the build if an input is missing. The build validates the map checksum,
imports the cells and FCC structures, verifies copied files, and includes the datasets in the
portable archive and installer. Without all inputs and that setting, builds
continue without these optional files and say so in the build output and manifest.
The same staging step is available to native Linux release builds, but this
particular release has only been packaged on Windows.
