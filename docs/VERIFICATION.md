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
