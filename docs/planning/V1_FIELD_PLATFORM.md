# Veilbreaker 1.0: field platform requirements and proposed delivery

Updated October 25, 2026. Requirements record and proposed sequencing; not an approved implementation design or a statement that these features have shipped. The user selected **in-app downloadable packs** on October 25; implementation details below remain proposed.

## Product requirement

The user defines 1.0 as a usable field application with terrain, line-of-sight assessment and tower information available in the build. Calculators, references and operator observations should help explain connectivity alongside measured cellular, Wi-Fi, network and SDR evidence. A concrete pillar, for example, can be observed by the operator even when the receiver cannot identify the cause of a signal change.

Terrain/LOS/tower workflows are mandatory for 1.0, not optional post-release additions. Existing import primitives alone do not satisfy field readiness. The user also requests the capabilities represented by WLAN Pros Toolbox; the [complete documentation inventory](WLANPROS_FEATURE_INVENTORY.md) retains all 270 entry headings against the publisher's advertised 264 tools. Completion of that entire broad catalogue before 1.0 has not been agreed.

## Existing foundation and material gaps

| Area | Existing foundation | Work still needed |
| --- | --- | --- |
| Offline mapping | Local map packs, CONUS overview prepared, GPS map and cached report imagery | Guided area preparation, coverage/age/storage visibility and offline field qualification |
| Cell references | Local SQLite import, full LTE identity matching, explicit operator LTE/NR records, ambiguity retained | Obtain authorized real datasets, integrated acquisition/update workflow and representative field validation |
| Physical towers | Cell reference locations and bearings | Separately sourced physical structures, owner metadata and explicit links to cells where evidence supports them |
| Terrain / LOS | Single GeoTIFF, Earth curvature, antenna heights, geometric profile and optional Fresnel clearance | Regional multi-tile coverage, acquisition/cache management, datum handling across tiles and real field validation |
| Reporting | Embedded reports, maps, cellular statistics, SDR spectrum/waterfall and survey comparisons | Environmental annotations and reproducible calculator results attached to survey context |
| Toolbox | Network diagnostics and several embedded RF/geographic computations | Searchable standalone tools, common input validation, saved results and sourced offline references |

Evidence: [mapping queue](../MAPPING_QUEUE.md), [cell references and terrain guide](../cell-references-and-terrain.md), [roadmap](../ROADMAP.md). Existing component presence is not proof of full tool parity or device qualification.

## Delivery alternatives

1. **Recommended: integrated data packs.** Ship the application, calculators and references; manage separately downloadable basemap, regional terrain, cell-reference and imagery packs inside the application. Prepare an area online, use it offline. Show sizes and coverage before download; support importing packs from removable storage. Existing CONUS overview is the initial basemap candidate, subject to distribution terms.
2. **Bundled national dataset.** Distribute a large optional offline media bundle alongside the installer. Convenient for disconnected deployment but expensive to build, distribute and keep current; elevation resolution and imagery make size highly variable. Do not promise nationwide street-level imagery or high-resolution terrain without measuring source coverage and size.
3. **Manual imports only.** Lowest development cost, but leaves the current data preparation burden on operators and is a poor fit for the requested 1.0 experience.

Use the current PySide6 desktop and shared Python engine. A registry of calculators, reference articles and diagnostic actions is preferable to hundreds of unrelated screens. Each entry needs an ID, category, search terms, input/output units, offline requirements, sources, revision and optional survey attachment support. Service lookups must visibly distinguish local cached knowledge from internet-dependent results.

## Proposed phases, ordered by field value

### A. Make terrain, towers and LOS operational

- Add an area preparation workflow showing required packs, coverage, source, license, date, resolution and storage size. Download resumably to a temporary location; verify integrity before registration. Preserve the prior usable version on failure.
- Introduce a terrain catalog and deterministic tile selection. Record horizontal/vertical reference systems and units. Report gaps or incompatible vertical references rather than interpolating unknown elevations as zero.
- Separate physical structures from estimated cell locations. A mast owner is not necessarily the serving carrier. Nearby structures and PCI matches are candidates, not positive identification. Full identity matches must retain dataset uncertainty and age.
- Retain the existing receiver/antenna heights, frequency, curvature choice and clearance assumptions in every saved profile. Terrain-only clearance does not establish a building/vegetation-free radio path.
- Keep tower-provider credentials user supplied and outside exports. Validate current provider terms, availability and redistribution permission before shipping actual data packs; no dataset is assumed to be acquired by this plan.

Acceptance: prepare a known area, disconnect networking, reopen the installed application, match a known cell where reference coverage exists, display a terrain profile, save it to a survey and reopen its report. Exercise absent coverage, conflicting candidates, nodata, failed downloads and expired credentials. Qualify Windows and Linux installations with real data.

### B. Establish the field toolbox

First set: dBm/mW/W conversion, wavelength, free-space loss, EIRP, cable loss, link budget/fade margin, Fresnel clearance, curvature, distance/bearing and coordinate conversion. Reuse existing verified geographic/terrain calculations rather than creating divergent formulas. Follow with noise-floor estimates, antenna downtilt, IPv4/IPv6 subnetting, MTU/MSS and PoE budgets.

Each result must show input values and units, assumptions, applicability, calculation version and practical interpretation. Changing frequency or antenna height must not overwrite a recorded measurement. Allow attaching a calculation snapshot to a survey/point and including it in reports. Validate independent known examples, unit conversions, invalid ranges and boundary cases before release.

### C. Add environmental observations and references

Within a survey point: **Add observation** → choose feature/material → optionally locate it on the map or attach a photo → describe dimensions/conditions → link relevant measurements → save. Support concrete/reinforced concrete, metal, coated glass, interior walls, foliage, water, people/vehicles and unknown material. Indoor observations must work without GPS; use point-relative descriptions until floor-plan positioning is implemented.

Minimal record: stable ID, survey/point/run links, author, timestamp, feature type, material (including unknown), free text, optional position and accuracy, photos and provenance. Optional dimensions, thickness, orientation and moisture must carry known/estimated/unknown states. Never require invented thickness or reinforcement values.

Keep three kinds of information visibly separate:

- **Measured:** radio and network values with source, timestamp and acquisition limitations.
- **Observed:** what the operator reports seeing, with optional supporting photos.
- **Modeled:** a calculated scenario with explicit assumptions, model revision and uncertainty.

For a concrete pillar, report possible obstruction, reflection or diffraction as explanations to investigate. Offer a repeat measurement on either side or along a short route, maintaining device, band, antenna orientation and test conditions where possible. A signal difference alone does not establish the pillar's material loss or prove multipath. Do not label a generic material as a universal dB penalty.

Reference subjects: absorption, reflection, diffraction, scattering, polarization, Fresnel obstruction, multipath, body loss, foliage/moisture and frequency dependence. Each short article should explain what can be observed, what can be measured, relevant assumptions, a practical next test and source/date. Start with original explanations informed by [ITU-R P.2040-4](https://www.itu.int/rec/r-rec-p.2040/en) for building materials and [ITU-R P.526](https://www.itu.int/rec/R-REC-P.526/en) for diffraction. Validate the applicable model and edition before implementing numerical predictions. Do not imply full 3D ray tracing.

Acceptance: annotate a pillar with and without GPS, associate before/after measurements, reopen/export the survey, and retain the distinction between observation, correlation and modeled explanation. Missing photos or unknown material properties must not prevent report generation.

### D. Expand diagnostics and reference coverage

Build out the inventory in field-value order: reachability/path visualization, DNS, TLS/HTTP inspection, discovery, channel/reference tables, signal interpretation and troubleshooting guidance. Some tools need network access or platform-specific privileges; state prerequisites and unavailable states. Add broader cabling, power, protocol and education topics through the same searchable interface.

Classroom simulations, historical tone generators, travel topics and branded handout subjects remain catalogued for prioritization. Implement useful equivalents using original text and assets; do not bundle publisher PDFs or reproduce proprietary layouts. Resolve their inclusion in the initial release explicitly instead of declaring the entire catalogue complete.

## 1.0 completion checklist

- [ ] Authorized, usable cell/tower data and regional terrain can be prepared through the application.
- [ ] CONUS overview and prepared survey areas work offline; coverage and missing layers are clear.
- [ ] Terrain/LOS/Fresnel reports are reproducible and retain uncertainty and assumptions.
- [ ] Physical structures, estimated cell locations and serving-cell identification remain distinct.
- [ ] Foundational toolbox and environmental references work without an external browser.
- [ ] Observations, measurements and calculation snapshots survive survey editing, reopen and export.
- [ ] Real phone/SDR surveys and failure/recovery paths are qualified on supported Windows/Linux builds.
- [ ] Installer lifecycle, source attribution, data licensing and release documentation are verified.

Selected delivery approach: in-app downloadable packs. Next, specify Phase A's pack catalog, provider adapters, coverage display, download/recovery lifecycle and offline acceptance cases, then implement in bounded increments. Do not start all 270 inventory entries at once.
