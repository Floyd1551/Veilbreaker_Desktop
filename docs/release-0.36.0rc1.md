# Veilbreaker 0.36.0rc1 — survey report imagery

- Saved offline map registrations show zoom range, size, source date and missing files.
  Removing a registration preserves the original archive.
- Survey details includes **Prepare report map**: explicit USGS NAIP aerial download,
  offline georeferenced PNG/JPEG import, preview, and regeneration from cached imagery.
- Survey reports embed annotated photographic context with numbered measurement
  points, legend, north arrow, approximate scale and provenance. The same report
  works in-app and as standalone HTML without a network connection.
- New evidence exports include original imagery, annotated PNG and metadata in
  their checksum manifest. Failed/cancelled replacement preserves saved imagery.
- Changes in survey membership or qualified positions flag the overlay as outdated.
- The prepared CONUS overview remains a separate optional map pack, outside Git
  and the installer. Tower matching and terrain/LOS remain future work.

## Validation

209 source tests passed, including image validation/projection, attachment integrity,
missing/stale imagery, portable export checksums, provider limits/errors, and native
worker cancellation. A real small-area USGS NAIP extract near downtown Dallas was
prepared and visually checked in the native report viewer; labels render correctly
with the Windows platform font backend. The headless offscreen backend on this host
has no fonts, so native rendering is the visual acceptance check.

Acquisition date remains Unknown when unavailable; the service copyright date is
retained only as attribution. This is aerial photography, not live satellite data.
Linux source support is retained; this Windows release does not claim a Linux
installer or Linux graphical validation. No new hardware field trial was performed.

See [offline map and imagery instructions](offline-maps.md) for import requirements.

Windows portable release qualification passed frozen CLI selftest, Unicode
analysis-worker/evidence verification, six-page GUI smoke checks and offline map
rendering/selection. A 20-point native imagery preparation preview also passed.
