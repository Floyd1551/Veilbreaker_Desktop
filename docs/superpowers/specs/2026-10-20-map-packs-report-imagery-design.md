# Map packs and survey report imagery

Date: October 20, 2026. Status: approved; implemented and Windows release-qualified in 0.36.0rc1.

## Goal and scope

Provide usable offline CONUS context and a photographic overview of each survey
in both the in-app report and portable HTML. Preserve the existing 1–20-point
survey workflow, evidence integrity and offline report viewing. A vector CONUS
overview has already been prepared and verified; it is not photographic imagery.

This slice covers map-pack management and cached survey-area report imagery.
Cell-reference import, tower matching and terrain/LOS remain separately queued.
No PDF engine or nationwide high-resolution imagery download is required.

## Recommended approach and alternatives

Use the current Protomaps vector pack for national navigation, and prepare small
NAIP aerial-image extracts for individual surveys. This provides photographic
site context without a national raster archive. Label the source as aerial
imagery, even where users colloquially call it a satellite view.

An online-only image URL would make old reports dependent on connectivity and
changing provider content. A full national imagery archive would impose much
larger preparation and storage requirements. Neither is the default design.

## Map packs

Add a local map-pack list with name, source date, geographic bounds, zoom range,
size and availability. Register/import existing files using the current validator;
retain a chosen active pack across launches. The prepared CONUS pack remains
separate from Git and the installer. Removing a registration does not delete its
file or any survey evidence. Missing files offer re-selection; reports remain usable.

Initially select one active vector pack explicitly, as the current renderer does.
Automatic blending of national and regional detail packs is deferred.

## Survey imagery workflow

Survey details gains **Prepare report map**. Use the first qualified position per
run, consistent with the current map overview, to propose an extent with padding.
Show a preview and allow the operator to adjust the area. Point labels match the
survey numbering; missing GPS is counted and never replaced with zero.

Offer an explicit online preparation action and an offline import route. Online
preparation requests only the selected area from the imagery provider, with a
clear indication that its bounds will be sent. Opening, regenerating or exporting
a report must never trigger a hidden download.

First provider: USGS NAIP, after confirming the selected service's export endpoint,
coverage, georeferencing, limits and per-image provenance in implementation.
The USGS service documents CONUS imagery and public-domain downloads:
https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer
https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-national-agriculture-imagery-program-naip

For offline preparation, accept a bounded PNG/JPEG plus a validated georeferencing
sidecar with bounds, supported CRS, source, attribution and imagery date if known.
Arbitrary unreferenced photos cannot be used to position measurement markers.
Full GeoTIFF/JPEG2000 processing is a later adapter, avoiding a large GIS runtime
in the first installer.

Start with a maximum 2048-pixel image dimension and a 20 MiB download limit.
Validate decoded dimensions, format and returned extent before caching. Fetch in
a cancellable worker with finite timeouts and atomic writes. Keep a previous good
image when replacement fails. Large or widely dispersed surveys receive an
overview preview; never silently crop points to make a detailed image appear useful.

## Report content

Add **Survey area** near the beginning of the report, containing a static image,
numbered GPS points, a legend, north indicator and correctly computed scale.
Record the extent, CRS, imagery provider/attribution, image acquisition date or
date range where known, preparation timestamp, and mapped/missing point counts.
Fetch date must not masquerade as image acquisition date.

Keep original cached imagery and derived annotated image separate. Reports embed
the rendered image bytes rather than relying on a temporary path or online URL.
Use the same asset and metadata for native viewing and standalone HTML. Include
the assets and hashes in new survey evidence exports without rewriting original
run bundles. An already-exported report retains its original imagery when the
cache or survey changes.

If imagery is unavailable, offer a clearly labelled vector overview or omit the
image with an explanation. Never label a vector map as satellite/aerial imagery.
Without qualified GPS, request an explicit operator-defined area and label it as
manually selected; do not imply that the phone measured that location.

## Reproducibility and updates

Store imagery under survey-owned assets, not global temporary storage. Metadata
includes the image checksum, source, bounds/CRS and the run IDs/positions used in
the overlay. Changed survey points or positions mark the overlay out of date and
offer regeneration from the cached image if coverage is sufficient. Recovered
surveys retain their assets; recoverable deletion follows the existing survey
lifecycle. Clearing a diagnostic workspace does not delete survey imagery.

Do not infer live conditions, building heights, cell-tower identity or LOS from
the photograph. Those require separately qualified evidence and later features.

## Verification and acceptance

- Existing CONUS archive passes structural validation and offline rendering (done).
- Pack register/select/remove/relink works without deleting source files or evidence.
- Synthetic georeferenced imagery places known points correctly, including edges,
  missing coordinates, bad extents and unsupported CRS; invalid images are rejected.
- Failed/cancelled fetches leave the previous valid image intact and UI responsive.
- Native and exported HTML show the same image, labels and attribution while offline.
- Exported reports still work after moving files to another directory and removing
  the live imagery cache; asset hashes verify in a new survey export.
- Existing surveys with no imagery continue to open and export normally.
- Preview tests cover one point, 20 points and widely separated survey points.
- A real small-area NAIP preparation is checked for geographic alignment and date
  handling before provider support is claimed.

## Implementation sequence after design approval

1. Write a scoped implementation plan with source/test touchpoints.
2. Add pack registration and cached imagery metadata/storage.
3. Implement georeferenced offline image import and report embedding first.
4. Add explicit bounded NAIP preparation using the same validated cache contract.
5. Validate native/portable reports, then package the release.
