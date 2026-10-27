# Regional terrain and structure packs

Date: 2026-10-27. This is the next bounded increment of the approved in-app downloadable-pack direction. Existing map, cell-reference and terrain assessment behavior remains available.

## Operator workflow

Configuration opens **Regional data packs**. The operator can import a local self-contained GeoTIFF terrain file or a Veilbreaker structure GeoJSON file, or download either from an explicit HTTPS URL. Before installation, the app asks for name, source, license/terms, source date and, for terrain, vertical datum and elevation units. Structure packs also require a declared WGS84 bounding box. The app shows file size, computed SHA-256, coverage, provenance, availability and data class after installation. A source URL's query string is never persisted.

Installed terrain packs can be selected from the existing path-assessment dialog, which fills the verified local path and source metadata. The assessment still requires explicit antenna heights, frequency and confirmation. A pack's raster bounding rectangle does not prove no-data-free coverage. One assessment still uses one GeoTIFF; adjacent-tile profiles remain pending.

Physical-structure packs are a separate local reference class. They contain points, IDs and optional owners/heights. They never identify the serving cell, carrier or antenna. Declared bounds describe the dataset extent, not completeness; absence of a structure record is not evidence that no structure exists. Cell-reference matching stays separate.

## Storage and validation

Packs live under the configured app data directory, outside Git and the installer. Each installed pack has a versioned manifest with kind, source, license, source date, import time, SHA-256, bytes, WGS84 bounds and format-specific details. Install to a private staging folder, validate and hash the copied bytes, then atomically register it. Cancellation, bad input or failed download leaves existing packs untouched. Normal listing checks availability/size; an explicit Verify action recomputes the hash. Deletion requires a GUI confirmation and does not rewrite saved surveys or reports.

Terrain uses the existing strict GeoTIFF validator, including known horizontal CRS, vertical datum and units. Structure input is bounded GeoJSON Point data with unique structure IDs and finite WGS84 coordinates. Its provenance is operator-supplied; no FCC ASR or OpenCellID affiliation is assumed. Download requires an explicit HTTPS URL and applies size, timeout, cancellation and optional expected-checksum checks. It stores the source host/path without credentials or query parameters.

## Scope limits

This increment provides managed import/download and a path-assessment handoff. It does not ship any national dataset, scrape a tower site, download a provider's data without operator selection, auto-associate a structure with a carrier, or join terrain tiles. Source-specific discovery (USGS TNM product search, FCC ASR adapter and authorized OpenCellID download) remains a follow-on once the core pack contract is tested with real data and terms.
