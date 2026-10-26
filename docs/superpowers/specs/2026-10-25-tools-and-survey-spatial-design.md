# Visual toolbox and indoor survey placement

October 25, 2026. User requested a dedicated Tools sidebar destination, Configuration rename, visual calculators, useful offline references, manual survey placement and heat maps. The user selected both geographic maps and floor-plan images and approved phased implementation of this design. Phase A is implemented in source; phases B–D remain pending.

## Tools workspace

Keep the existing native PySide6 application and offline behavior. Tools becomes a searchable workspace with Calculators, References and Charts tabs. Configuration retains hardware checks, receive presets and recovery. Settings retains persistent diagnostic configuration. Existing keyboard shortcuts keep their destinations; Tools receives Alt+7.

Calculator selection should show purpose, input units, result cards, diagram and interpretation together. Start with the existing tools, then add distance/bearing, coordinate conversion, IPv4 subnetting, MTU/MSS and PoE budgets in separate tested increments. These are standalone tools; running one must not start acquisition or modify recorded metrics.

Use native vector painting for diagrams, so offline builds and high-DPI screens do not depend on a remote renderer. Fresnel: endpoints, selected point, first-zone envelope, 60% boundary and labeled radius. Earth curvature: direct path, geometric/effective Earth curves and selected bulge. Explicitly mark diagrams as schematic with vertical exaggeration; antenna heights and real terrain must not be invented. Warnings from calculator validity checks appear beside results and diagrams. Text results remain accessible without interpreting colors. Export the diagram with its calculation snapshot in a later report integration step; do not let an image lose input provenance.

Initial original reference material: dB versus dBm/dBi, power and loss relationships, RSSI versus RSRP/RSRQ/SINR, interference versus thermal noise, Fresnel/LOS, polarization, reflection/diffraction/absorption, channel width and throughput, Wi-Fi versus cellular identifiers, IPv4/CIDR, DNS/DHCP/MTU and basic network troubleshooting. Charts use units, sources and applicability. Thresholds are technology/service-specific guidance rather than universal pass/fail bands. Regulatory/channel allocations require current US sources and dates. Do not copy publisher handouts or imply these references replace measurements.

## Manual placement

Survey detail gains a spatial workspace with Geographic map and Floor plan views. Select a planned point or existing attached scan, choose Place point, click a location, review its label/floor and save. Allow reposition and clear placement with explicit confirmation of what changes. Placement must work before and after capture. All existing runs remain unchanged.

Geographic placement stores latitude/longitude as operator-supplied coordinates. Floor placement stores floor-plan ID and normalized x/y image coordinates, optional building/floor labels and optional operator-entered elevation. Image coordinates must never be relabeled as GPS or converted into fabricated latitude/longitude.

Import local PNG/JPEG floor plans into survey-managed storage, with dimensions, content hash and bounded decoded size. Multiple floor plans can represent different floors. Store positions normalized to the image, independent of zoom/window size. Replacing a floor-plan image requires a new identity or an explicit re-registration workflow; preserve positions on the old image rather than silently moving them. Removing a floor with linked scans requires resolving those placements first.

Optional calibration: choose two image points and enter their real-world separation, with units. Without calibration, placement and measured-point coloring work, but no meter-based distance/coverage radius is claimed. Photos of angled drawings may need rectification; the first version expects a plan viewed from above, not arbitrary perspective reconstruction.

Store a versioned spatial sidecar per survey using the existing lock/atomic-write pattern, referencing stable survey point/run IDs. Keep original GPS in evidence alongside manual placement. Show placement source, operator-entered accuracy where known, timestamp and edit history. Export floor plans and placement sidecars in survey bundles; remove/restore them with the survey lifecycle. Avoid storing sensitive host file paths in portable exports.

Use a distinct marker style for manual positions. Automatic tower/terrain reasoning continues to require qualified measured GPS unless a separate explicit manual-location assessment is requested. Do not silently promote a manual pin into qualified capture GPS.

## Heat-map stages

1. **Measured-point map:** color positioned scans by a selected metric, showing numeric value, unit, source, age and available identity. Works with sparse data and without AP identity. Empty/missing values stay missing. Separate floors, measurement sources, survey visits and signal types; never combine RSSI with RSRP or uncalibrated SDR power.
2. **Optional estimated surface:** only after sufficient comparable, spatially distributed points and a calibrated floor/map area exist. Use documented interpolation with a user-visible coverage radius, mask outside the sampled footprint, exclude large gaps and display samples over the surface. Collinear or duplicate-position-only datasets cannot produce a 2D surface. Never interpolate across floors; wall/room constraints require explicit geometry and are not inferred from pixels. Show that the surface estimates values between measurements and is not a propagation simulation.

Lack of AP identity does not prevent a measurement map. It does prevent attributing the map to a single AP. Separate modes: connection experience (identity may change, transitions visible) and identified-transmitter coverage (requires stable BSSID or full cell identity). On a DAS, shared cell identity need not distinguish individual remote antennas; label results as observed service coverage rather than inventing which remote served each sample. Neighbor cells, serving cells and SDR observations remain separate.

Initial metrics: serving-cell RSRP/RSRQ/SINR where actually exposed, compatible Wi-Fi RSSI, and network latency/loss/throughput with units. SDR mapping requires compatible frequency range, receiver gain, antenna/setup and capture settings; defer its interpolation until that comparability is enforceable. One scalar per positioned scan must identify its aggregation window/statistic and retain the full underlying time series.

## Implementation phases and acceptance

A. Dedicated navigation (implemented), then visual calculators and initial references. Check seven-page navigation, small-window/high-DPI rendering, diagram consistency against numeric outputs, unknown states and offline operation.

B. Survey sidecar and geographic/floor-plan placement. Check click-to-coordinate conversion under pan/zoom, multiple floors, calibration, asset integrity, reassignment, clear placement, reopen and portable export. Confirm original evidence hashes do not change. Reject updates on completed surveys until reopened.

C. Measured-point metric coloring and legends. Check missing values, changing/unknown identifiers, source/band filters and repeat visits. Verify no invented measurements or AP attribution.

D. Guarded interpolation and report snapshots. Validate known synthetic fields, sparse/collinear samples, masks, floor separation and deterministic exports. Record algorithm/version, filters and parameters with output.

No national dataset download or new transmission capability is part of this change. Keep current 20-point survey cap; revisit it separately after the spatial workflow is qualified.
