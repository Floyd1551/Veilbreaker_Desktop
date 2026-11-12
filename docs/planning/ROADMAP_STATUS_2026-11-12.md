# Veilbreaker roadmap status — November 12, 2026

This is a source-code status snapshot, not a release certification. The Desktop
source reports 0.67.0rc1 and the latest mobile debug build reports 0.8.25-dev.
The available 0.67.0rc1 Windows installer predates the recent Desktop changes;
it has not been rebuilt for them. The mobile builds after 0.8.13 have not been
visually qualified on the phone in these passes.

## Desktop field platform and 1.0 gates

- [x] Foundations in source: Windows/Linux CLI and Desktop, evidence/reports,
  receiver inputs, surveys, manual positions and floor plans.
- [x] Offline basemap foundation and a supplied CONUS overview; regional terrain
  and cell/structure data can be prepared with coverage and provenance. The
  overview is not a guarantee of detailed nationwide coverage.
- [x] Terrain profile, curvature, Fresnel and LOS assessment paths, including
  multi-tile sampling and no-data warnings. These are modeled terrain results,
  not proof of unobstructed real-world radio propagation.
- [x] Local OpenCellID MCC 311 reference snapshot and physical-structure data
  workflows. Reference positions and candidates do not prove serving-tower
  identity; the snapshot is not a complete nationwide tower inventory.
- [x] Searchable offline tools and references, survey observations, calculation
  attachments and measured-point visualizations have implemented foundations.
- [ ] Qualify the complete field workflow: prepare a real area, disconnect,
  reopen map/data, inspect candidates, run LOS and reopen its report.
- [ ] Verify real-device and recovery paths on supported Windows/Linux builds;
  validate area coverage, licenses, installer lifecycle and release signing.
- [ ] Complete broader authorized tower/cell coverage, reliable area packs,
  full no-data checks and any licensed offline imagery required for deployment.

## Mobile 1.0 direction

- [x] Unified Android application, public-API cellular capture, explicit SIM
  choice, GPS, cached Wi-Fi inspection, local reports and Desktop USB protocol.
- [x] Offline toolbox baseline: 38 calculators, two converters, 53 references,
  10 guides, and initial Wi-Fi, FWA and topology planning aids. Models are not
  validated coverage predictions or measured evidence.
- [x] Initial cellular workflow: readable live metrics, sample/response timing,
  capture and review shortcuts, and contextual measurement explanations.
- [x] Local mobile surveys and explicit capture archive, each bounded to 20;
  archive copies can be added to an open survey.
- [x] Desktop can review mobile-survey exports, preserve original files in a
  separate local library, preview recorded locations, extract captures and
  attach a selected capture as diagnostic input. The library supports recoverable
  Trash without changing source bytes and a separately confirmed permanent
  removal for intact trashed copies. No Desktop run is fabricated.
- [ ] Complete native mobile-to-Desktop survey conversion/attachment and point
  associations. Current local copies are separate from Desktop survey sessions.
- [ ] Finish the cellular vertical slice: interactive history, stronger event
  handling, save/review continuity and accessibility/usability validation.
- [ ] Complete a current-device screen-by-screen audit and competitor research;
  previous reconnaissance explicitly did not inspect all competitor screens.
- [ ] Qualify the current build on physical phones: permissions, multiple SIMs,
  cached data, interruption/recovery, large text, TalkBack and battery behavior.
- [ ] Production signing, upgrade/migration strategy and release testing remain.

## Next work

1. Validate the current Android build and new transfer workflow on the phone and
   installed Desktop without disturbing saved captures or device credentials.
2. Design and implement native Desktop survey attachment of mobile points,
   preserving source bytes, timing, notes and location provenance; handle
   duplicates, partial failure, recovery and existing evidence explicitly.
3. Return to the 1.0 field gates for terrain, tower candidates, LOS and offline
   regional data, including real-area qualification and installer refresh.
4. Continue high-value toolbox and visual workflow improvements after core
   evidence capture, persistence and transfer are dependable.

There is no defensible completion percentage until the remaining workflows and
device/field qualification are measured against the release criteria.
