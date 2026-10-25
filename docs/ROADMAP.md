# Veilbreaker Desktop roadmap

Updated October 25, 2026. Current working versions: **Desktop 0.41.0rc1**, **Companion 0.5.1-dev**.

**Revised 1.0 requirement:** usable terrain, LOS and tower information are release
requirements. Integrated calculators, references and operator environmental observations
extend the field survey workflow. See the [requirements and proposed delivery sequence](planning/V1_FIELD_PLATFORM.md)
and [WLAN Pros capability inventory](planning/WLANPROS_FEATURE_INVENTORY.md).
The inventory is research, not a claim that its features are implemented. The user
selected in-app downloadable data packs; detailed pack-manager design and the initial
toolbox scope remain to be finalized.

First toolbox increment (source): [offline RF field calculators](rf-field-calculators.md)
provide power conversion, wavelength, free-space loss, EIRP and link budget/margin,
plus Fresnel clearance, Earth bulge, thermal/receiver noise and cable loss. Results
can be copied or exported as text/JSON with inputs and assumptions. Survey attachment and installer packaging of
this increment remain pending.

Latest mapping queue: [CONUS maps, local cell references and terrain LOS](MAPPING_QUEUE.md).
The offline GPS viewer, map-pack registration, report imagery, local cell-reference
matching and regional terrain assessment are implemented. National basemap acquisition,
real reference data and field qualification remain tracked in that queue.
Version 0.35.0rc2 fixes Android USB pairing cleanup; a full phone-fed diagnostic
was confirmed on the connected device. Historical milestones below retain their
original scope and qualification notes.

Latest field-workflow increment: source-labelled phone findings and hypotheses, qualified SDR baseline comparisons, Clear workspace, recoverable test/survey removal, and survey landing/detail lifecycle. See [field workflow guide](field-workflows.md).

Previous increment: phone-approved six-digit USB pairing, automatic credential exchange, and an in-app Cellular field report with per-cell identity, signal statistics and trends. Broader phone qualification and production signing remain pending; phone/GPS position evidence and offline maps are implemented.

Build a dependable local diagnostic companion for Windows and Linux: capture a problem, understand what the evidence supports, choose the next measurement, and compare results after a change. The desktop and CLI share one engine. Missing measurements remain unknown.

This roadmap consolidates the recovered inventory, current source, README, local release artifacts and verification record. Completed means implemented; qualification is stated separately. Earlier verification entries describe their release at that time: manual survey progression, for example, was pending in 0.12 and delivered in 0.13. Future priorities below are proposed sequencing, not promised dates or assigned release versions.

## Current position

| Area | Status | What remains |
| --- | --- | --- |
| Source recovery and desktop foundation | Implemented | Compare against any newer NetworkHub source if supplied |
| Evidence integrity and acquisition recovery | Implemented and regression tested | Physical failure qualification across supported devices and OSes |
| HackRF receive workflows | Implemented; bounded live 2.4 GHz captures verified | Reconnect, busy/timeout, broader bands, firmware and endurance qualification |
| Cellular and Starlink | Collectors and reasoning implemented | Live device qualification and sanitized regression fixtures |
| Survey investigations | Sessions, templates, repeat visits, maps, report imagery and saved-run attachment implemented | Complete guided investigation flow and field qualification |
| Settings and advanced tools | Network and common hardware forms implemented; advanced JSON and CLI available | Remaining advanced forms and guided workflows |
| Windows distribution | Local frozen build and installer lifecycle recorded as passing | Clean-machine testing, locale coverage, signing and update decisions |
| Linux distribution | Ubuntu 24.04 x64 CI passed source/frozen checks, rendered maps and Debian lifecycle | Physical Linux desktop and Wayland qualification |
| Public release | Local release-candidate artifacts available | Qualification gates and publication; no remote release documented |

The 0.19.0rc1 source consolidates the work since the original recovery baseline. Local Windows validation is recorded below; public release availability and GitHub CI results are separate from local qualification.

## Accomplished

### Recovery and retained diagnostic engine

- [x] Verify all 46 original recovery artifacts against their supplied hashes; preserve the originals outside the checkout.
- [x] Recover the 0.9.3 multimodem engine and pass its embedded self-test.
- [x] Package a shared Python engine with desktop and CLI entry points.
- [x] Retain metric normalization, findings/severity, data-quality and health indices, ranked hypotheses, supporting/contradicting evidence and suggested next tests.
- [x] Retain 25 diagnostic hypothesis categories and six scenario profiles spanning cellular, private networks, voice, telemetry and satellite service.
- [x] Retain site/scenario baselines, similarity to operator-confirmed cases and CLI case management.
- [x] Retain Windows/Linux host, route, interface and Wi-Fi collection; ping/DNS, guided follow-up, path/PMTU tests and configured iperf3 throughput.
- [x] Retain read-only modem discovery/AT telemetry with generic 3GPP, Sierra EM9 and Quectel RM5xx/RG5xx parsers.
- [x] Retain Starlink telemetry through optional Python integration or external grpcurl, optional gpsd input and external JSON adapters.
- [x] Retain SQLite history/cases, text/HTML/JSON reports and raw capture evidence. These implementations do not establish live qualification for every collector.

### Desktop and installation foundation — 0.10.0rc1

- [x] Build the native PySide6 workspace: diagnostics, history, tools/readiness, SDR and settings; later add Site surveys as the sixth page.
- [x] Add synthetic demo and offline metric import, report inspection, saved-run reopening and same-site/scenario comparison.
- [x] Run long operations in cancellable worker processes.
- [x] Add platform-aware per-user storage, legacy data reuse, Unicode exports, configuration validation and explicit missing-config errors.
- [x] Prevent host-only evidence from presenting as healthy service; distinguish missing comparison values from zero.
- [x] Correct throughput acquisition to measure forward and reverse directions separately.
- [x] Build Windows portable CLI/GUI bundles and a per-user Inno Setup installer with shortcuts and data-preserving uninstall.
- [x] Implement Linux archive/deb packaging, per-user install/uninstall scripts and Windows/Linux CI build automation.
- [x] Add build manifests, dependency notices, checksums, frozen-runtime checks and installer lifecycle tooling.
- [x] Discover HackRF tools without changing system PATH; save raw sweep CSV, settings and logs; display median/maximum spectra.

### Evidence and reliability — 0.10.1rc1 through 0.10.3rc1

- [x] Add versioned SHA-256 evidence manifests and desktop/CLI verification; detect changed, missing, extra and duplicate entries and label legacy archives unverified.
- [x] Add live collector progress, outcomes, durations, metric counts, notes and per-metric provenance.
- [x] Preserve collection metadata in evidence and history; label imports and partial acquisition explicitly; return CLI exit code 3 for saved partial acquisition.
- [x] Report missing expected measurement groups, including each requested SDR range and both throughput directions.
- [x] Write durable atomic checkpoints and recover interrupted metrics/partial SDR CSVs offline without repeating acquisition.
- [x] Protect active workers, prevent duplicate recovery and preserve original evidence when retrying after reconnect.
- [x] Add spectrum zoom, pan, hover readout, expanded inspector, compact setup controls and small-screen scrolling/navigation.
- [x] Cover cancellation, stopped-worker recovery, missing hardware and reconnect/retry behavior with automated fixtures. Physical device qualification remains open.

### Repeatable RF workflows — 0.11.0rc1

- [x] Add bounded receive presets for 2400–2500 MHz, 600–1000 MHz and 5150–5850 MHz.
- [x] Expose sweep count, requested bin width and valid LNA/VGA gain controls; keep amplifier and antenna power off in presets.
- [x] Record discovered receiver serial and capture settings.
- [x] Overlay saved before/after medians and export per-bin differences with run references, settings and raw-file hashes.
- [x] Reject numeric comparison for mismatched/unknown hardware or settings, incomplete grids and interrupted captures.
- [x] Compare two existing real 2.4 GHz captures successfully. Broader preset availability is not broader live qualification.

### Survey investigations — 0.12.0rc1 through 0.14.0rc1

- [x] Group 1–20 named tests into a saved survey with mixed diagnostic selections and stable survey/run links.
- [x] Show side-by-side metrics and observed-count/minimum/median/maximum summaries; preserve missing values.
- [x] Export survey JSON, comparison CSV, original evidence ZIPs and an umbrella integrity manifest.
- [x] Preserve completed results after interruption and integrate recovered diagnostic runs.
- [x] Add manual pause/continue between physical points, audited point notes, original settings snapshots and explicit continuation of only unrun steps.
- [x] Protect sessions against concurrent workers; keep settings snapshots local and out of exports.
- [x] Save/load portable queue templates without acquiring data; create independent evidence for each new visit.
- [x] Compare same-site visits by exact unique point label, independent of queue order; export comparison JSON.
- [x] Withhold numeric changes for incomplete collections or incompatible selections/scenarios/settings; report missing or ambiguous points.

### Everyday settings — 0.15.0rc1

- [x] Add validated ping/DNS targets and optional iperf3 server/port fields, including IPv6 support.
- [x] Preserve hardware/storage configuration when saving network fields and never start diagnostics on save.
- [x] Keep advanced JSON behind a toggle with synchronization and unsaved-edit conflict protection.

## Verification accomplished and its limits

| Evidence | Recorded result | Boundary |
| --- | --- | --- |
| Source regression suite | 104 tests passed on October 5, 2026; frozen checks also passed | Synthetic/automated coverage is separate from physical qualification |
| Windows frozen runtime | CLI, worker and six desktop pages passed in latest recorded build | Current development host, not a clean machine |
| Windows installer | 0.19.0rc1 install/reinstall/uninstall passed on October 5, 2026 | Isolated validation identity preserved the existing installation |
| Live host collection | Windows passive collection returned 32 host/link/Wi-Fi metrics | Insufficient evidence for overall service health |
| Live HackRF | Source and packaged 2400–2500 MHz captures succeeded; 300 samples/100 bins | Specific device/tools/settings only; relative RF power, not calibrated dBm |
| Survey execution | Frozen passive batch and manual pause/resume workflows passed; bundles verified | No new RF or active network qualification from these checks |
| Visual checks | Collection, spectrum, survey, comparison and settings screens reviewed; scaling check recorded | Full accessibility and supported-display matrix still pending |
| Linux | Build/CI and installation tooling present; shell syntax checked | Native execution and installation results not documented |

Detailed historical results and log locations are in [VERIFICATION.md](VERIFICATION.md). Local release artifacts include the 0.19.0rc1 Windows installer, portable ZIP and checksums. Builds and installer checks are historical evidence unless explicitly rerun; roadmap editing does not itself requalify a release.

## Pending roadmap

### Phase 1 — Trust the diagnostic record: implementation complete

Maintain the delivered integrity, provenance, partial-result and recovery guarantees as new collectors and workflows are added. The remaining physical failure qualification is tracked in Phase 2.

Completion gate for future changes: unavailable requested evidence never appears as successful acquisition; measurements retain sources; cancellation leaves no worker behind; recovered evidence reopens and verifies; failure regression checks pass.

### Phase 2 — Dependable hardware workflows: highest priority

- [ ] **P1 — Qualify HackRF failure handling:** physical unplug/replug, busy device, timeout, missing dependency and disconnected discovery. Verify clear outcomes, released handles and recoverable evidence.
- [ ] **P1 — Qualify repeat captures:** test all offered preset ranges, supported device/tool/firmware combinations and longer sessions; reconstruct displayed summaries from retained CSV/settings/logs.
- [ ] **P1 — Qualify cellular modems:** actual available Sierra, Quectel and generic devices; registration/signal coverage, port selection, unsupported fields, disconnect and timeout behavior; retain sanitized fixtures.
- [ ] **P1 — Qualify Starlink:** actual terminal/backend combinations, normal/degraded/unavailable states and optional location behavior; retain sanitized fixtures.
- [ ] Publish the supported hardware/firmware/tool matrix with explicit tested and untested entries.

Dependencies: physical devices, host tools/drivers and repeatable test conditions. Exit: supported devices pass connect/disconnect, busy, timeout and dependency checks; every result is traceable to raw evidence. Transmission and firmware modification remain outside scope.

### Phase 3 — Guided investigations: foundation delivered, workflow expansion pending

- [x] **P2 — Common hardware settings forms:** delivered in 0.17; advanced acquisition forms remain future work.
- [ ] **P2 — End-to-end investigation flow:** site/connection selection → readiness → capture → evidence review → suggested follow-up → record a change → compare.
- [x] **P2 — Searchable history:** full run history in 0.16; survey search/state filtering in 0.19.
- [x] **P2 — Baseline and long-term trends:** per-point numeric trends across visits with gaps, exclusion reasons, guarded statistics and JSON/CSV exports in 0.19.
- [x] **P2 — Desktop confirmed-case management:** entry/review/withdrawal in 0.18; event history, search/paging, export and source reopening in 0.19.
- [x] **P2 — GPS and maps foundation:** phone/receiver location evidence, offline survey maps, report imagery and local references are implemented. Real field accuracy and broader device qualification remain open.
- [ ] Add dedicated forms for remaining advanced CLI workflows where needed to complete the investigation journey.

Dependencies: stable collection metadata/settings snapshots; GPS hardware for field qualification. Exit: complete and reopen a before/after investigation without CLI commands or JSON editing; comparable evidence, uncertainty and missing data stay explicit.

### Phase 4 — Platform qualification and deeper diagnostics: implementation/qualification gaps

- [ ] **P1 — Native Linux qualification:** source and frozen CLI, X11/Wayland desktop, workers/cancellation, evidence, per-user installer/uninstaller and Debian install/remove; retain successful CI/native results.
- [ ] **P1 — Clean Windows qualification:** install without Python/admin rights, shortcuts, CLI/desktop, dependencies, reinstall/upgrade/uninstall and preservation of config/history/evidence.
- [ ] **P1 — Define the supported OS/architecture matrix:** current Linux target is Ubuntu 24.04 x64; older glibc distributions and ARM need native builds and evidence before support claims.
- [ ] **P2 — Non-English Windows measurements:** replace or qualify English-dependent ping/netsh parsing.
- [ ] **P2 — Real network test qualification:** forward/reverse throughput against actual iperf3 servers, PMTU and failure scenarios on carrier/private networks.
- [ ] **P2 — Explicit interface selection/binding:** establish which link is measured before adding simultaneous multi-WAN comparison workflows.
- [ ] **P3 — Separate engine components:** split collectors, reasoning and persistence behind existing regression coverage as workflow complexity warrants.
- [x] **P3 — Android interoperability contract:** versioned captures, saved inputs and bounded live USB sessions are implemented. General synchronization and production APK signing remain open.
- [ ] Compare recovered Desktop source with newer NetworkHub material if it becomes available and reconcile any missing work.

Platform qualification can proceed alongside Phase 2 when machines are available. Exit: reproducible artifacts, native evidence for each supported OS/device combination, intended-link measurements and data-preserving upgrades.

### Phase 5 — Consumer application finish and broad release: pending

- [ ] **P3 — Navigation and onboarding:** guide first installation, readiness, first useful capture and reopening/sharing evidence.
- [ ] **P3 — Presentation pass:** plain language, typography, spacing, visual identity, spectrum interaction and report readability.
- [ ] **P3 — State handling:** consistent empty/loading/error states and practical recovery instructions.
- [ ] **P3 — Accessibility:** keyboard access, focus order, readable contrast, scaling and representative display sizes.
- [ ] **P3 — Representative user validation:** users can install, capture, interpret limits and share a report without coaching.
- [ ] Decide signing, update delivery and public distribution before broad release; qualify the chosen release path.
- [ ] Review and commit the accumulated implementation, complete release notes/checks, and publish an approved release after its qualification gates pass.

Dependencies: reliability and supported-platform gates. Exit: common user journeys and failures pass functional/visual checks, support boundaries are documented and distribution is ready.

## Recommended next milestones

| Order | Deliverable | Completion evidence |
| --- | --- | --- |
| 1 | Hardware qualification pack, starting with HackRF | Physical failure/repeat-capture logs, verified bundles and a device/tool matrix |
| 2, parallel where equipment permits | Linux and clean-Windows qualification pack | Native build/runtime/install/upgrade results and an OS matrix |
| 3 | Hardware forms and guided before/after investigation | Desktop-only workflow completed and reopened with intact evidence |
| 4 | Search, trends, cases and mapped surveys | Multi-visit fixtures plus field checks where GPS is used |
| 5 | Intended-link diagnostics and Mobile import design | Bound-interface network tests and a documented versioned import contract |
| 6 | Consumer finish and release readiness | Accessibility/user checks, distribution decision and release qualification |

No completion percentage is assigned: feature implementation, field qualification and release readiness are different kinds of work. Dates and device-specific commitments depend on equipment and platform access.

## Scope boundaries and delivery discipline

- Preserve the CLI, original evidence, recovery backups and existing installations; deliver small tested increments.
- Distinguish synthetic fixtures, live measurements, packaged-runtime checks and OS/device qualification in every release record.
- Evidence hashes establish file consistency, not authorship or measurement accuracy. Diagnostic scores are heuristic rankings, not calibrated probabilities.
- RF levels remain relative; calibrated RF measurements, protocol identification and interference-source attribution are not delivered promises.
- Native PDF reports are not implemented; recovered PDF/image examples are references. A native PDF feature requires a scope decision.
- Multi-WAN imagery does not establish simultaneous interface measurements or failover control. Failover control is not an agreed deliverable.
- Android/Mobile source is a separate project; its existence does not imply Desktop synchronization.

Sources: [README](../README.md), [recovered inventory](PROJECT_INVENTORY.md), [reconstruction history](PROJECT_RECONSTRUCTION.md), [verification record](VERIFICATION.md), current source/tests and local release artifacts.

## October 2 GUI increment — 0.17.0rc1

Delivered after this roadmap's initial inventory: 0.16 searchable history across all saved runs, followed by 0.17 responsive workspace navigation/actions, persistent task progress/cancellation, metric filtering, keyboard shortcuts, explicit diagnostic request summaries, contextual empty/selection states and common hardware connection forms. The Phase 3 searchable-history item is implemented. Hardware forms now cover modem port/driver/backend, Starlink host/port/backend and HackRF tools/serial; advanced acquisition controls remain future form work. Full accessibility, guided investigations and hardware/platform qualification remain pending.


## October 5 field-workflow increment — 0.19.0rc1

Delivered multi-visit trends using the selected survey as a baseline, with comparable-only statistics, explicit gaps, an accessible values table, and JSON/CSV export. Added saved-survey search/state filtering and draft point rename/reordering. Extended confirmed cases with timestamped confirmation/withdrawal events, transactional writes, withdrawal reasons, search/state/paging, JSON export and source reopening. Existing evidence and legacy cases are preserved. Full guided investigations, GPS/maps, live hardware qualification and native Linux qualification remain open.

## Site survey reporting — 0.24.0rc1

Implemented native viewing and portable HTML reports for existing 1–20-point surveys, with collection/assessment separation, saved notes, complete-test numeric summaries and explicit measurement gaps. Survey exports include the report in the integrity manifest. Hardware, GPS and platform qualification remain separate milestones.

## Guided comparison increment — 0.25.0rc1

Extended the existing baseline comparison with persistent ordered-visit change notes, native report viewing and HTML/JSON export with provenance. Comparison eligibility remains guarded by complete collections, matching settings, scenarios and test selections. This delivers the record-change/review-comparison segment of Phase 3; the full readiness-to-follow-up guided journey remains open.

## Guided follow-up increment — 0.27.0rc1

Next tests now provides detailed requirements, procedures and bounded setup preparation for supported recommendations, plus settings/readiness navigation. Preparation does not start acquisition or alter site/scenario. Unsupported procedures remain manual. A fully integrated investigation journey and hardware qualification remain open.

## Selected-test readiness — 0.28.0rc1

Delivered a worker-based prerequisite checklist linked from diagnostic setup and Tools. Checks are scoped to current selections, distinguish missing/configured/available/untested, and show snapshot provenance. They do not establish connectivity, hardware qualification or successful acquisition.

## Android import foundation — 0.29.0rc1

Added versioned Android envelope validation, explicit native observation/serving-cell review, original-byte evidence preservation and offline analysis. Optional GPS metadata is validated and retained. Companion APK, survey attachment and physical phone qualification remain future phases; this is not live Android receiver support.

## Android companion source increment — October 11, 2026

Added an initial snapshot-only Kotlin companion and Android CI workflow. Includes public LTE/NR cell observations and JSON export matching the Desktop contract. Compilation/qualification status is recorded in android-companion/README.md; source implementation is not physical compatibility evidence. Timed sessions, lifecycle tests, phone qualification, production signing and survey attachment remain open.

## Android diagnostic input — 0.30.0rc1

Saved Android captures now attach to Run diagnostic instead of starting a standalone import. Phone measurements, source time and original evidence share the run with selected collectors while retaining separate RF interpretation. Clear the attachment to remove it. Live USB sessions and survey queue attachment remain pending; USB design is in docs/superpowers/specs/2026-10-13-android-usb-input-design.md.

## Android live USB input — 0.31.0rc1

Companion 0.2 adds armed foreground USB sessions. Desktop selects an authorized USB device, requests bounded samples and retains raw sessions plus per-cell ranges/change/age summaries in the normal diagnostic evidence bundle. Saved captures remain an alternative input. Tokens are ephemeral and excluded from retry history. Physical-device qualification, survey-queue attachment and stable APK signing remain pending.

### 0.31.0rc2 Windows USB discovery fix

Verified against the connected Samsung: Windows platform-tools 37.0.1 omits USB bus paths and rejects devices --proto-text. Fall back to ADB's USB-only -d get-serialno selector; refuse ambiguity instead of inferring transport from serial shape. Existing companion APK remains compatible.


## Capture reasoning and saved survey inputs - 0.38.0rc1

Implemented freshness-qualified phone capture patterns (repeated weak signal, recovered quality dips, primary-cell identity changes) and complete-sweep SDR persistence, brief activity and broad power-rise findings. Findings retain source labels, counts, limitations and field follow-ups in native and exported reports. Saved diagnostics can now be linked into open surveys from history or survey details. See [release behavior and thresholds](release-0.38.0rc1.md). Physical receiver qualification and validated phone-bound service correlation remain future work; these rules do not prove interference or alter desktop health scores.

## Cellular visibility — 0.39.0rc1 / Companion 0.5.0-dev

Desktop reports and Companion previews now separate latest registered connections, observed neighbors, and an observed-band inventory. Modem-reported bands remain distinct from channel-derived candidates, including unresolved NR overlaps. Incomplete identities remain separate and current connections take priority over historical display entries. See [release behavior and limits](release-0.39.0rc1.md). Physical Samsung qualification and production APK signing remain open; Android's public API is not an exhaustive all-band scan.

## Platform qualification follow-through — October 23, 2026

[Linux CI](https://github.com/Floyd1551/Veilbreaker_Desktop/actions/runs/39833926282/job/120017114783) passed for 0.39.0rc1, including software-rendered offline maps and Debian installation/removal. Windows CI stopped at map rendering; a local frozen check passed with explicit software rendering. CI now retains qualification artifacts even on failure and prints map failure reports from the windowed executable. These runner settings do not change normal application rendering. [Windows and Linux qualification](https://github.com/Floyd1551/Veilbreaker_Desktop/actions/runs/39963411791) now passes release checks and installer lifecycles. Neither CI nor local synthetic tests replace physical device acceptance.


## Guided field survey detail — 0.40.0rc1

Added next-point guidance, passive readiness against saved point settings, explicit manual/batch capture actions, and review of the latest attempted point. Worker completion/cancellation refreshes the current survey journal. Stale readiness responses are discarded and completed surveys remain protected. See [release behavior](release-0.40.0rc1.md). Live phone capture directly inside survey queues remains separate work; phone diagnostics can already be attached as existing runs. The broader end-to-end investigation milestone remains open.


## Live phone survey points — 0.41.0rc1

Survey details can now pair an authorized USB phone and capture directly into the next unrun point, using its saved diagnostic settings. Each phone capture pauses after one point, including in batch surveys; pairing credentials are transient and changed point/settings contexts are rejected before acquisition. Partial phone evidence stays attached to its point. See [workflow and limits](release-0.41.0rc1.md). Real Samsung survey qualification and automatic multi-point phone sessions remain open.
