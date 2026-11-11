# Veilbreaker Mobile 1.0: reconnaissance and proposed direction

Status: preliminary, 2026-11-11. Prepared for review; no implementation approved by this document.

## Evidence and limits

This assessment examines the 0.8.13-dev Android README, manifest, navigation, survey store and planning draft codec, alongside the user's directive and Android/provider documentation. It is a targeted repository review, not yet an exhaustive audit. ADB confirmed an awake device and the presence of Veilbreaker, Network Survey, Net Analyzer, G-MoN Pro and Wi-Fi Analyzer packages. A work-profile package listing returned a permissions error. No competitor workflows or new screenshots were captured in this pass; claimed features below are documented or user-supplied, not independently observed. No accessibility, field, performance or device-matrix certification is implied.

## Current architecture and capability

* Android 10+; Kotlin and Android Views, target SDK 35. One foreground `MainActivity` hosts Live, Diagnose, Survey, Reports and Tools; Wi-Fi and GPS use separate activities. Preserve the application ID and USB session lifecycle when changing navigation.
* Public Android APIs provide selected-SIM cellular observations, including serving/neighbor roles where reported, signal values and sample age. The live trend is bounded and session-only; Android responses are not guaranteed fresh. Data is not a complete raw modem feed.
* Wi-Fi shows connection and cached nearby observations; the chart is based on reported primary frequencies, not measured utilization. Network testing is a bounded HTTPS request, not a complete speed test. USB inventory identifies possible hardware but does not operate an SDR.
* Surveys group up to 20 explicitly added captures. `MobileSurveyStore` uses validated, bounded app-private JSON and Android `AtomicFile`, with serialized transactions. Export exists; mobile survey import into Desktop remains unsupported. The latest capture is separately exportable to JSON/PDF.
* GPS provides foreground location, an operator-supplied bounded image and an opt-in online street basemap. It is not a licensed downloadable offline map. OpenCellID lookup is user initiated; results are community estimates, not verified tower positions.
* Tools include searchable offline calculators, references and guides, plus schematic Wi-Fi, FWA and topology planning. Wi-Fi/FWA input drafts persist; topology and tuning comparisons are session-only. Saved FWA coordinates currently lose OpenCellID source metadata, although the interface warns of that limitation.
* Desktop pairing uses an explicit short code and localhost USB transport with bounded foreground sessions. Preserve its existing capture schema and import compatibility during any mobile redesign.
* Tests cover model, collection, survey, map, tooling and USB behavior. README reports no Gradle wrapper or production signing. Instrumented accessibility, crash recovery, performance and multi-device coverage still need a measured baseline.

## Screen and journey review: hypotheses to verify on device

Severity is a provisional impact assessment based on source and documented behavior, not an observed usability test.

| Workspace / journey | Evidence | Impact | Recommended next check |
|---|---|---|---|
| Live → cellular capture | SIM setup, collection and detailed analysis span multiple views; direct setup shortcut exists | High | Time a first capture; show readiness, missing permissions and recovery alongside the primary action |
| Diagnose → cellular | Foreground monitor ends on exit, SIM change or five minutes; trend is not saved | High | Make active, stopped, stale and unsaved states unmistakable; connect an explicit save action to existing capture contract |
| Diagnose → Wi-Fi / GPS | Separate activities cannot be opened while USB session is active | Medium | Explain the reason and safe next action at the point of navigation; verify back behavior |
| Survey → capture → export | 20-point local survey; mobile survey JSON cannot yet be imported by Desktop | High | Walk through interrupted collection and transfer; surface export destination and current transfer limitation |
| Reports → detail | Latest capture offers serving and neighboring cell inspection; broader history/project association remains limited | High | Validate finding, freshness, original evidence and next action are visible together |
| Tools → planning | Offline calculations exist; topology and trial comparisons do not persist | Medium | Make session-only status obvious and verify a draft reopen; preserve source of candidate coordinates |
| Maps | User image and opt-in online OSM layer with differing coordinate assumptions | Medium | Make provenance, coverage, offline availability and provider terms visible |
| All screens | No current screenshot or TalkBack/large-text sweep in this pass | Unknown | Capture real screens, measure touch targets/contrast and test large fonts before assigning visual defects |

## Reference application matrix

Sources: [Network Survey repository](https://github.com/christianrowlands/android-network-survey), [NetMonster Core repository](https://github.com/mroczis/netmonster-core). Product behavior from the directive is a lead for inspection, not an independent finding. Offline cells below mean the proposed Veilbreaker requirement.

| Reference | Capability / engineering value | Proposed Veilbreaker implementation | Feasibility / offline | Priority | Verification |
|---|---|---|---|---|---|
| Network Survey | Unified start/stop, selected record types and destinations; documented cellular/Wi-Fi/Bluetooth/GNSS and streams | One visible survey session with explicit collectors, local journal and separately enabled export | API and permissions dependent; local capture offline | P0 | Upstream README; installed UI not inspected |
| NetMonster Core | Telephony normalization, validation and compatibility helpers | Evaluate against our raw/derived model and device fixtures before adopting | Plausible offline; API/dependency compatibility unverified | P1 | Repository documentation; not the installed NetMonster app |
| Network Analyzer | Dashboard, signal cards and test shortcuts | Home cards linking to source-specific detail and tests | Feasible offline for local data; online tests explicit | P1 | User-described; installed UI not verified |
| Net Analyzer | Interface addresses, routes and DNS presented for inspection | Actionable address/interface detail with scoped tests | Android exposure varies; local details offline | P1 | User-described; package present, UI not inspected |
| LTE Discovery | Cell details, neighbors and freshness | Serving/neighbor table with explicit timestamps and unknown fields | Android and modem limited; offline | P0 | User-described; installation/UI not verified |
| G-MoN Pro | Field logging, export and mapping | Compare explicit field sessions and portable evidence export | Export formats to validate; offline collection | P1 | User-described; package present, UI not inspected |
| WiFiman | Discovery, visual analysis and performance flows | Task-oriented diagnostics with explicit network/endpoint scope | API and permissions dependent; connectivity as needed | P1 | User-described; installation/UI not verified |
| Wi-Fi Analyzer | Frequency/channel visualization | Verify widths and freshness and link chart to observed networks | Android scan restrictions; cached offline data | P1 | Package present, UI not inspected |

Both referenced repositories identify Apache-2.0 licenses. Review exact revisions, notices, transitive dependencies, data licenses and compatibility before any reuse; no source or assets have been copied. NetMonster dependency maintenance/version and Android 10–16 behavior remain unverified.

## Proposed information architecture and design system

Five peer destinations: **Home** (current state and active recording), **Analyze** (cellular, Wi-Fi, network and device workspaces), **Survey** (capture and spatial work), **Tools** (calculators, models and references), **Projects** (saved captures, surveys, reports and transfer). Settings remains accessible from the header; preserve current routes and deep links as aliases during migration. This is a proposal: test whether Projects and Survey are sufficiently distinct before moving existing data.

Adopt shared Android Views components first: status/permission banner, metric card with unit and freshness, source badge, accessible action row, observation table, recording strip, empty/error state, chart and detail sheet. Retain navy/cyan; pair every color with text and a numeric value. Support system font scaling, screen readers and at least 48 dp targets. Test contrast and daylight use rather than assuming colors pass. Offer overview → analysis → engineering detail without hiding missing data or replacing numbers with a generic signal score.

## Measurement and storage architecture

Keep capture JSON and Desktop adapter intact. Introduce an internal observation envelope around existing producers, rather than rewriting parsers: technology, source, nullable value/unit, observation and receipt times, sample age or unknown, role, subscription scope, identity, derivation, permission state, location provenance and uncertainty. Distinguish Android-reported, external instrument, operator-entered, calculated, cached and estimated. Do not relabel receipt time as measurement time. Version any persisted changes and implement read-old/write-new migrations with fixtures and rollback/export tests. Never turn a manual map point into GNSS evidence.

Build a local project index referencing immutable captures and surveys; preserve original payloads and identifiers. Define export/transfer version negotiation before Desktop survey import. Map adapter should separate renderer, provider, tile policy, storage and attribution. MapLibre is a candidate, not a commitment: its offline API does not supply imagery rights. [OSM standard tiles prohibit bulk prefetch and offline regions](https://operations.osmfoundation.org/policies/tiles/); use an appropriately licensed provider or self-hosted data for packs.

## Five improvements with the greatest field impact

1. **One cellular journey:** SIM, permissions, live status, freshness, start/stop and save in one coherent workspace.
2. **Evidence that explains itself:** observed value, source, age, limitations and context together; preserve originals through report and transfer.
3. **Reliable survey-to-Desktop flow:** persist and recover locally, show transfer state, and import versioned survey bundles without duplicating points.
4. **Actionable network views:** gateway/DNS/interface details connect to explicitly scoped tests with clear results and cancellation.
5. **Field-ready navigation and readability:** consistent status strip, larger touch targets, legible metric cards, accessible chart alternatives and clear offline states.

## Prioritized backlog and acceptance criteria

| Priority | Task and dependency | Acceptance criteria |
|---|---|---|
| P0 | Baseline UI and competitor evidence | Capture consented screens and complete common tasks; label unavailable items; measure TalkBack, font scale, target sizes and failures |
| P0 | Cellular vertical slice; retain current acquisition | Select SIM, inspect serving and neighbors, see age/source, record/save and reopen; permission loss, cached/missing data and stop states are clear |
| P0 | Evidence schema and Desktop compatibility | Round-trip old fixtures and partial captures; unknown values remain unknown; reject unsupported versions without data loss |
| P0 | Survey reliability and transfer | Interrupt/restart and storage failure tests preserve committed points; versioned mobile bundle imports with stable IDs and visible conflict handling |
| P0 | Release hardening | Signed reproducible release, upgrade/rollback, crash and permission tests, physical-device matrix, offline/export validation and documented privacy behavior |
| P1 | Persist FWA source and planning drafts | Reopen old drafts safely; retained candidate shows source, time, license and uncertainty; edits clear stale attribution |
| P1 | Contextual diagnostics and references | User can open an explanation or explicitly start a scoped test from a metric; no hidden external traffic |
| P1 | Map providers and licensed offline regions | Attribution, coverage, storage and provider disclosure visible; measurements accessible with network disabled |
| P2 | Terrain, LOS, instrumentation and advanced modeling | Only after validated data rights and hardware; label model assumptions, uncertainty and unsupported devices |

## First vertical slice and migration

Start with **Cellular: inspect → monitor → save → review** because the existing acquisition, SIM selection, live trend and capture serializer already form a reusable path. It validates the highest-value design components and provenance model before multiplying them across modules. Retain the existing screen as a safe route during rollout. First document real-device flow and wireframes; add a UI adapter over existing collection, then deliver overview/analysis/detail, explicit state and contextual help, followed by save/review using the established schema. Keep existing USB protocol untouched. Test with old fixtures, no permissions, two SIMs, unavailable metrics, stale/duplicate samples, disconnect, rotation, process recreation and TalkBack. Do not interpret a 5G display override as a measured NR cell.

## Release milestones and open research

1. Complete screen captures, competitor comparisons and architecture/data-flow audit; review the migration spec.
2. Deliver and validate the cellular slice, then apply shared components to Wi-Fi/network.
3. Complete project/survey persistence, recovery and Desktop interchange.
4. Add licensed mapping and contextual references; keep terrain/LOS/instrument work honest and bounded.
5. Complete release signing, accessibility, privacy, performance and hardware qualification before 1.0.

Open: inspect each competitor's accessible UI, settings, offline and export behavior; verify implementations only from public sources; assess third-party licenses and dependencies; profile battery/startup/charts on actual hardware; measure usability and recovery with representative field tasks. No 1.0 date or completion percentage is defensible before these checks.

## Primary references

* [Android telephony API and cache/update limitations](https://developer.android.com/reference/android/telephony/TelephonyManager); [Wi-Fi scanning and throttling](https://developer.android.com/develop/connectivity/wifi/wifi-scan).
* [Android accessibility for Views](https://developer.android.com/guide/topics/ui/accessibility/views/apps-views); [Android navigation patterns](https://developer.android.com/design/ui/mobile/guides/layout-and-content/layout-and-nav-patterns).
* [Nielsen usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/); [MapLibre Android offline API](https://maplibre.org/maplibre-native/android/api/-map-libre%20-native%20-android/org.maplibre.android.offline/).
