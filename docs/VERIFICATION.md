# Local verification — 0.10.0rc1

September 30, 2026. Windows 11 x64, Python 3.13.15, PySide6 6.11.2, PyInstaller 6.22.0. See the packaged `build-manifest.json` for installed package versions.

## Completed checks

- All 46 original backup artifact hashes match the supplied inventory.
- The recovered 0.9.3 synthetic self-test passed before modification.
- 22 automated tests pass: recovered reasoning/parser tests, Unicode exports and history, confirmed-case persistence, legacy/platform paths, config/input errors, no false healthy status from host-only evidence, native ping flags, directional throughput, comparisons, GUI worker analysis/errors/cancellation/history, and SDR discovery/parsing validation.
- Windows passive native collection returned 32 host/link/Wi-Fi metrics. The rebuilt engine marks this as insufficient evidence for service health. No active Internet test was needed for this check.
- Frozen CLI self-test, offline Unicode analysis worker, five-page GUI rendering, and GUI-launched worker/history smoke checks pass in the Windows bundle. Final builds repeat these checks before producing archives.
- The Windows installer lifecycle passed: current-user install, registry entry, both shortcuts, installed CLI and GUI, reinstall, uninstall and preservation of user config/data. Logs and the latest result are under `test-artifacts/installer-report.json`.
- Linux shell installer syntax was checked with Bash. This is not native Linux runtime qualification.

## Real HackRF evidence

Radioconda's `hackrf_info`/`hackrf_sweep` 2024.02.1 and libhackrf 0.9 detected the connected device. Host tools reported board ID 5 with unknown board/firmware naming (API 1.09). No firmware or driver changes were made.

Three receive-only sweeps over 2400–2500 MHz completed with 1 MHz bins, LNA gain 16 dB, VGA gain 20 dB, amplifier off and antenna power off. Veilbreaker captured 300 samples across 100 unique frequency bins, saved an evidence ZIP and SQLite run, reopened the run and rendered the real spectrum in the desktop UI. The first direct host-tool test also completed successfully.

Recorded application run: `20260930-133427-8116dd`. Its strongest sample was at 2459.5 MHz, with relative power -12.5 dB; the median sample level was -61.94 dB. These are uncalibrated levels from a short capture, not dBm measurements, protocol identification or proof of interference. Raw CSV, capture settings and logs support the result. Subsequent captures may differ as nearby transmissions change.

Evidence lives in the per-user Veilbreaker data folder, not the source repository. `test-artifacts/hackrf/spectrum.png` is a screenshot of the actual saved capture in the application. Unknown firmware naming remains a collector note even though this bounded sweep succeeded.

## Not yet verified

- Native Linux execution, Linux GUI rendering on X11/Wayland, Linux installation lifecycle and .deb installation. The supplied CI includes these checks, but it has not run here; this host has no Linux runtime.
- Clean Windows machine installation, code signing, non-English Windows ping/netsh output, or compatibility across all Windows/Linux versions and CPU architectures.
- Live Sierra/Quectel/other modems, Starlink terminals, full SDR range, calibrated RF measurements, or extended-duration acquisition.
- Physical throughput, PMTU and failure scenarios across real carrier/private networks. Directional throughput has fixture coverage, not an external server qualification result.

No remote release has been published. Linux readiness is implementation plus automation, not a claim of completed Linux qualification.

## Final SDR build recheck

The packaged CLI repeated the real 2.4 GHz capture successfully as run `20260930-133735-bd3cba` (300 samples, 1 MHz bins). The refreshed installer passed lifecycle testing using the same release payload and installer directives with a separate validation app ID/shortcut name, because a normal Veilbreaker installation was present by then. That existing installation was preserved. The earlier production-identity installer check also passed before the SDR additions. The latest machine-readable installer report explicitly records `isolated_identity: true`.

## 0.10.1rc1 — Phase 1 evidence integrity

- 30 source tests pass, including manifest tampering, missing/extra/duplicate entries, malformed manifests, legacy bundles, archive size limits and desktop verification dispatch.
- Windows frozen build passes CLI self-test, offline Unicode worker and five-page GUI smoke checks. Tools screenshot was visually reviewed.
- Frozen CLI generated an offline analysis bundle and verified all five manifest entries (`test-artifacts/phase1-frozen/verification.json`).
- New evidence contains application version and run metadata. Existing captures are not rewritten; older archives return unverified.
- No new hardware capture was required for this evidence-format increment. Previous HackRF qualification remains documented above. Native Linux qualification remains pending.
- Windows install/reinstall/uninstall lifecycle passed with an isolated validation identity using the same release payload. Existing user installation preserved. Logs: `test-artifacts/installer-2a5e833f`.

## 0.10.2rc1 — Collection outcomes and progress

- 37 source tests pass. New coverage includes optional absence, negative/zero observations, collector exceptions, source override order, missing HackRF sweeps, incomplete throughput, offline provenance and CLI partial exit code 3.
- GUI regression checks reopen collection metadata and older runs without it. A synthetic disconnected-device result was rendered and visually reviewed in the new Collection tab (`test-artifacts/acquisition-collection.png`).
- Frozen Windows CLI/GUI build passed, including worker progress events, imported metric provenance, evidence integrity verification and the existing five-page desktop smoke.
- No new live hardware qualification is claimed. Fine-grained command/measurement completeness, reconnect recovery, native Linux qualification and durable cancellation recovery remain roadmap work.
- Windows install/reinstall/uninstall checks passed using the isolated validation identity and the 0.10.2rc1 payload. Existing user installation preserved. Logs: `test-artifacts/installer-5b79d404`.

## 0.10.3rc1 — Reliability completion and spectrum layout

- 45 source tests pass. Added expected-measurement reporting, a real terminated-worker checkpoint recovery test, active-worker protection, idempotent recovery, reconstruction of partial SDR CSV data, reconnect/retry fixtures, and spectrum zoom/readout/compact-layout checks.
- Saved sub-1 GHz evidence was visually reviewed in the compact spectrum workspace and expanded 1280×720 inspector. A 150% scaling screenshot confirms small-screen scrolling and navigation access. No additional hardware acquisition was needed for this UI correction.
- Recovery does not contact hardware or restart active tests. Recovered runs are explicitly interrupted and retain their usable metrics and raw files. Device retry starts a new run after fresh discovery; original evidence is preserved.
- Physical unplug/replug qualification on each hardware/OS combination remains Phase 2 work. Native Linux qualification remains pending; mocked disconnect/reconnect tests are not a substitute for that qualification.
- Frozen Windows recovery was also exercised against a stopped-process checkpoint; the recovered evidence ZIP verified successfully (`test-artifacts/frozen-recovery/result.json`).
- 0.10.3rc1 Windows install/reinstall/uninstall checks passed with the isolated validation identity. Existing user installation preserved. Logs: `installer-29553332`.

## 0.11.0rc1 — Repeatable SDR workflows

- 54 source tests pass, including bounded preset settings, gain/resolution/device compatibility checks, interrupted and truncated capture rejection, median aggregation, delta direction, comparison provenance, preset dispatch and the comparison dialog overlay.
- Two existing live HackRF captures from September 30 were compared successfully: 100 aligned bins; median change −0.15 relative dB. The before/after inspector and preset controls were visually reviewed. This reuses saved evidence; it is not a new live capture qualification.
- A new discovery attempt reported “No HackRF boards found.” No new captures were taken and no transmission or firmware operation was performed. Physical device reconnect/busy handling and modem/Starlink qualification remain pending in Phase 2.

## 0.11.0rc1 completion

- Finished the pending release build after fixing a transient Windows checkpoint-replacement lock with bounded retries; the recovery regression test passes.
- Frozen Windows CLI/GUI checks and isolated install/reinstall/uninstall lifecycle passed. Logs: `test-artifacts/phase2-build.log`, `test-artifacts/installer-479b13d4`.

## 0.12.0rc1 — Survey sessions

- 63 source tests pass, including a full 20-step session, per-run evidence preservation, umbrella manifest verification, numeric summaries, mixed/failed steps, interruption without auto-resume, duplicate run protection, queue limits and GUI comparison of missing versus zero measurements.
- The survey results page was visually reviewed with a clearly labeled four-run synthetic baseline. Saved sessions hide the builder and present run results and metric comparisons together.
- Sessions currently execute sequentially without pauses at one position. GPS/map integration and manual walk-around progression remain future work. No new live RF qualification is claimed.
- Frozen v0.12.0rc1 CLI ran a real two-step passive host/network survey successfully; both steps completed and the umbrella evidence ZIP verified. No active traffic tests or SDR captures were requested. Logs: `test-artifacts/frozen-survey-check.log`.
- v0.12.0rc1 Windows install/reinstall/uninstall lifecycle passed using the isolated validation identity; existing user installation preserved. Logs: `installer-59137f9b`.


## 0.13.0rc1 — Survey field progression

- 66 source tests pass. New coverage verifies three-point manual progression, stable run IDs and original site settings, interruption continuation that skips attempted steps, concurrent-worker locking, audited note edits and unchanged original evidence.
- Frozen Windows CLI successfully paused and resumed a real two-point passive host/network survey; the final umbrella bundle verified. No active traffic or RF capture was requested. Log: `test-artifacts/manual-frozen.log`.
- Frozen CLI/GUI release smoke passed, including six desktop pages. Survey results, point-note controls and comparison layout were visually reviewed at 1280×900.
- Original settings snapshots stay local and are excluded from exports. Reopening never runs tests; continuation requires an explicit action. Legacy surveys without snapshots cannot resume.
- GPS/maps, physical device reconnect qualification and native Linux execution remain pending.
- Windows 0.13.0rc1 isolated install/reinstall/uninstall lifecycle passed; existing user installation preserved. Logs: C:\Users\floyd\Development Projects\Veibreaker-Desktop\test-artifacts\installer-eb2aaa3b.


## 0.13.1rc1 — Reusable survey templates

- 70 source tests pass. Added template round-trip, version/size/flag validation, failed-save preservation, exclusion of visit data, independent evidence across repeated visits, and GUI load-without-acquisition checks.
- Survey builder and template actions visually reviewed at 1280×900. Loading displays the plan before the existing explicit Run survey action; current site, targets and receiver settings apply.
- Templates contain labels, diagnostic flags and pause mode, excluding point observations, run IDs, results and configuration. GPS/maps and native Linux qualification remain pending.
- Frozen Windows CLI/GUI checks and isolated install/reinstall/uninstall lifecycle passed for 0.13.1rc1. Existing user installation preserved. Logs: C:\Users\floyd\Development Projects\Veibreaker-Desktop\test-artifacts\installer-0f6d77b7.


## 0.14.0rc1 — Repeat-visit comparison

- Added same-site baseline comparisons matched by exact unique point labels, independent of queue order. Numeric changes require complete collection, matching test selections/scenarios and matching saved settings. Missing observations remain unknown.
- Regression coverage includes signed changes and zero, missing/reordered points, settings snapshots, ambiguous labels, partial collections, nonnumeric/nonfinite values, evidence immutability and desktop JSON export.
- Comparison dialog visually reviewed using explicitly synthetic before/after data; missing RF readings show no change value. No new live hardware qualification is claimed.
- GPS/maps and native Linux qualification remain pending. Matching settings cannot establish identical hardware or field conditions.
- 77 source tests, frozen Windows CLI/GUI checks and isolated install/reinstall/uninstall lifecycle passed for 0.14.0rc1. Existing user installation preserved. Logs: C:\Users\floyd\Development Projects\Veibreaker-Desktop\test-artifacts\installer-c24363b1.


## 0.15.0rc1 — Everyday network settings

- 80 source tests pass, including hostname/IP/IPv6 validation, optional throughput configuration, port bounds, preservation of hardware configuration, rejected-save preservation, no acquisition on save and advanced-edit conflict handling.
- Settings page visually reviewed at 1280×900. Common fields are visible by default; advanced JSON remains available behind an explicit toggle.
- Recovery test polling now tolerates a transient Windows sharing violation while the worker atomically replaces its checkpoint, within the existing bounded timeout.
- No new hardware or native Linux qualification is claimed.
- Frozen Windows CLI/GUI checks and isolated install/reinstall/uninstall lifecycle passed for 0.15.0rc1. Existing user installation preserved. Logs: C:\Users\floyd\Development Projects\Veibreaker-Desktop\test-artifacts\installer-d0e552f1.


## 0.16.0rc1 — Searchable history

- 82 tests pass. Added 405-run paging/search coverage, literal wildcard/quote handling, stable timestamp ties, previous-run lookup across pages and GUI selection reset/search beyond the first page.
- Search does not change saved evidence. Previous-run selection ignores the visible search filter; spectrum candidate lookup is independent of that filter.
- No new hardware or native Linux qualification is claimed.
- History UI visually reviewed at 1280x900. Frozen Windows CLI/GUI checks and isolated install/reinstall/uninstall lifecycle passed for 0.16.0rc1. Existing user installation preserved. Logs: C:\Users\floyd\Development Projects\Veibreaker-Desktop\test-artifacts\installer-ef55749f.

## 0.17.0rc1 — GUI workflow improvements

- Responsive navigation and wrapping controls, workspace-wide task progress/cancellation, keyboard page navigation, metric filtering, diagnostic request summaries and contextual history/survey actions implemented.
- Added tabbed cellular/Starlink/HackRF connection forms with validation, atomic combined saves, preservation of acquisition/privacy settings and protection of unsaved form/JSON edits.
- Automated checks cover 760-pixel layouts across all six pages, selection/empty states, filtering with zero values and provenance, cancellation, settings rejection and preservation, and no acquisition on save.
- No new hardware or Linux qualification is claimed. Screenshots are under `test-artifacts/gui-enhancements`.


## 0.18.0rc1 — Desktop confirmed cases

- Added confirmed-case entry, review and withdrawal from Run history. Explicit operator verification is required; withdrawn records remain visible and are excluded from future similarity matching. Original run evidence and past reports are preserved.
- Integration coverage exercises the desktop entry point, disabled save before confirmation, recording a cause/resolution, withdrawal and unchanged source data. Cause/resolution lengths are validated in the shared store.
- Case dialog visually reviewed with synthetic data and uses scrolling on smaller screens. History actions now wrap to preserve narrow-window access.
- No new hardware or native Linux qualification is claimed.
- 94 source tests, frozen Windows CLI/GUI checks and isolated install/reinstall/uninstall lifecycle passed for 0.18.0rc1. Existing user installation preserved. Logs: C:\Users\floyd\Development Projects\Veibreaker-Desktop\test-artifacts\installer-b42f6e1e.


## 0.19.0rc1 — Survey trends, organization and case history

- Source suite passed 103 tests before final release validation. Added coverage for chronological/gap-preserving trends, zero/non-numeric readings, settings incompatibility, ambiguous points, CSV formula-safe text, offline CLI/UI export and unchanged original evidence.
- Queue tests cover rename/reordering, preserving selections, rejecting duplicates and avoiding duplicate generated labels after removal. Survey filters cover sites, point labels and states.
- Case tests cover event ordering, idempotent withdrawal, atomic case/event rollback, legacy schema preservation, search, export and original run preservation. New case-event schema is additive; historical events are not invented for old records.
- Synthetic trend, survey organization and case screens were visually inspected, including a 700×620 trend window. Gaps are not interpolated and excluded observations do not contribute to statistics.
- No new live hardware or native Linux qualification is claimed. Preview fixtures are under `test-artifacts/field-workflows-preview`.

- Release validation exposed a frozen-Qt loader failure: dependency discovery had collected an unrelated ICU DLL from a host tool runtime on PATH. Windows packaging now isolates native dependency discovery to the project Python and Windows directories, leaves the host environment unchanged, and runs console-mode GUI smoke first so loader errors are visible. A regression check covers foreign PATH/plugin exclusion.

- Final October 5 validation passed: 104 source tests, frozen CLI and both console/windowed GUI smoke, and isolated install/reinstall/uninstall lifecycle for 0.19.0rc1. Logs: `installer-993fd578`. Existing installation preserved.
- Frozen CLI trend fixture returned 3 comparable observations across 5 visits, retained missing/incompatible gaps, and preserved all 10 original survey/run bundles byte-for-byte. Result: `test-artifacts/field-workflows-frozen-trend.json`.
