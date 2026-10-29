# Offline data in a release

The prepared Windows build can include the supplied CONUS overview basemap and
OpenCellID MCC 311 country export. In a new installation, the included basemap is
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
limitations. Observed bounds do not establish complete coverage. A map pack is
not terrain, satellite imagery, or a tower inventory; terrain and physical-site
datasets still need to be prepared separately.

## Rebuilding with local downloads

Downloaded data is deliberately excluded from Git. Stage these four local files:

- `map-packs/CONUS-overview-20261019.pmtiles`
- `map-packs/CONUS-overview-20261019.json` with its `sha256` and source metadata
- `offline-input/311.csv` (headered or headerless OpenCellID export)
- `offline-input/311.json` containing nonempty `source`, `license`, and `date` strings

Set `VEILBREAKER_OFFLINE_DATA_REQUIRED=1` before running `build-installer.ps1`
to fail the build if an input is missing. The build validates the map checksum,
imports the cells, verifies copied files, and includes both datasets in the
portable archive and installer. Without all inputs and that setting, builds
continue without these optional files and say so in the build output and manifest.
The same staging step is available to native Linux release builds, but this
particular release has only been packaged on Windows.
