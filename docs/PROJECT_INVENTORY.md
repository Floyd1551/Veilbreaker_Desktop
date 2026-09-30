# Recovered Veilbreaker Desktop inventory

Inspected September 30, 2026. This describes source-backed capabilities, separate from reference imagery and unverified hardware claims.

## Provenance

The supplied backup contains an inventory of 46 original artifacts. All 46 hashes matched `CONTENTS.csv`. It also contains an extracted Android project and an index. Original files remain unchanged.

The latest Desktop source was `Desktop/Source_Versions/Veilbreaker_v0.9.3_multimodem.py`, 254,084 bytes, SHA-256:

`9c47ac23f9e384a823a6f0eb87432b20e3be54806083bcb77212123d5667edf8`

The working engine was copied to `src/veilbreaker/core.py`. Desktop 0.9.0, 0.9.1 cross-platform, 0.9.2 Starlink, `veilbreaker_logic_engine.py` and its saved smoke test remain in the backup. The embedded 0.9.3 self-test passed before modifications. The backup is a collection of saved artifacts, not a verified image of NetworkHub's current filesystem; newer local changes may exist there. GitHub's Desktop repository had no commits when cloned. Mobile source was not modified.

## Implemented in recovered source

| Area | Implementation and limits |
| --- | --- |
| CLI | Configuration, readiness, platform inventory, collection, offline analysis, history, baselines, confirmed cases, modem, Starlink, SDR and path commands |
| Reasoning | Metric normalization, findings/severity, data-quality/health indices, ranked hypotheses, supporting/contradictory evidence and next-test recommendations |
| Context | Numeric site/scenario baselines, similarity matching against operator-confirmed cases, six scenario profiles |
| Windows | Host memory/uptime, PowerShell route/interface discovery, route fallback, netsh Wi-Fi, native ping/DF-ping |
| Linux | Host load/memory/temperature/uptime, ip networking, iw Wi-Fi, native ping/DF-ping, serial discovery and optional ModemManager hints |
| Cellular | Read-only AT collection via pyserial or Linux POSIX fallback; generic 3GPP, Sierra EM9 and Quectel RM5xx/RG5xx parsers |
| Modem selection | Conservative auto-discovery, forced driver/port selection, opt-in wider probing, optional raw responses and identifiers |
| Starlink | Local telemetry via optional `starlink_grpc` or external `grpcurl`; status, obstruction, path and alert reasoning; location opt-in |
| SDR | HackRF discovery and receive-only sweeps; CSV parsing, occupancy/noise/peak summaries, baseline context |
| GPS | Local gpsd collection when available, including position supplied by gpsd |
| Active tests | Ping, DNS, staged paths, IPv4 MTU estimation, configured iperf3 throughput; guided follow-up reasoning cycle |
| Adapters | Configured external JSON commands with field mapping |
| Persistence | SQLite runs/cases/metadata, WAL mode, metrics/report JSON and per-run artifact directories |
| Reports | Console text, HTML, JSON and evidence ZIP bundles with notes and recorded SDR files |

Synthetic tests do not establish hardware compatibility across every model, firmware or driver.

## Diagnostic scope

The professional engine has 25 hypothesis categories: weak cellular coverage; antenna/feedline degradation; RAN interference/loading; serving-cell/band instability; LTE-anchor impairment; NR-secondary impairment; modem thermal problems; registration failure; APN/core sessions; carrier/core/private-WAN paths; WAN impairment; local handoff; DNS; MTU/fragmentation; throughput; Wi-Fi access; Wi-Fi interference; device resources; SIM/device provisioning; abnormal SDR energy; satellite visibility; satellite transport; Starlink obstruction; Starlink terminal faults; and Starlink access/PoP paths.

Scores are expert ranking heuristics, not calibrated probabilities. SDR power is not automatically calibrated dBm or proof of an interference source. MTU estimates depend on ICMP responses and can be affected by filtering/loss. Collector errors must be reviewed alongside conclusions.

Profiles: `field_validation`, `cellular_fwa`, `private_apn`, `realtime_voice`, `remote_telemetry`, `satellite_wan`.

## References rather than Desktop implementation

- Three saved PDFs show network, MultiWAN and SDR report examples. The recovered CLI emits HTML/text/JSON, not native PDF.
- Desktop/network/SDR/MultiWAN images are concepts and previews. No Desktop GUI source was present.
- MultiWAN imagery does not establish simultaneous per-interface WAN measurement or failover control.
- Android archives 0.1.0–0.3.0 are separate Mobile work. The extracted 0.3.0 tree includes UI, cellular/Wi-Fi collectors, surveying and reporting code. Mobile integration is outside this rebuild.
- Branding includes a starter SVG pack and raster concepts. Desktop icons use the recovered SVG emblem.

## Changes in 0.10.0rc1

- Native PySide6 workspace: five pages, seven result tabs including saved spectrum, offline demo/import, evidence export, cancellable worker processes.
- Shared Python package with stable CLI and GUI entry points.
- Windows installer and portable bundle; native Linux archive/deb build tooling and per-user install script.
- Platform-aware user storage, legacy data reuse, UTF-8 exports, explicit missing-config errors, input/config validation.
- GUI/CLI saved-run comparison distinguishes missing values from zero and reports changes without assuming improvement.
- Host-only evidence becomes `INSUFFICIENT_EVIDENCE` rather than healthy. JSON retains the numeric health index for compatibility; interpret it with status/coverage.
- Separate forward/reverse throughput measurements fix the recovered code's incorrect interpretation of one run's sender and receiver totals as two directions. See [ESnet's reverse-mode documentation](https://software.es.net/iperf/invoking.html).
- Linux ping uses C-locale parsing; English Windows text limitations remain.
- Readiness uses a unique temporary write test rather than overwriting a fixed data-folder filename.
- HackRF tools can be located in Radioconda or an explicit directory without changing PATH. Real 2.4 GHz capture succeeded. Repeated sweep samples now preserve the correct bin width; raw CSV, tool output and acquisition settings are retained. Spectrum previews show median and maximum at each frequency.

## Architecture

```text
GUI (gui.py) → JSON request → worker (jobs.py) ─┐
CLI (cli.py / __main__.py) ────────────────────┤
                                            core.py
                                collectors → metrics → reasoning
                                           → SQLite + evidence
paths.py       platform/legacy storage selection
comparison.py  before/after metric differences
assets/        recovered emblem and rendered icons
```

Each desktop task owns its process and database connection. The recovered engine remains mostly in one module to avoid combining wholesale refactoring with recovery. Existing boundaries support a later split into collectors, persistence and reasoning modules.

## Installer precedent and open qualification

Network Provisioning Studio supplied the PyInstaller/Inno Setup pattern: per-user install, Start menu/optional desktop shortcuts, app ID, uninstall registration, checksums, smoke checks and data-preserving lifecycle tests. Veilbreaker has separate identity and storage.

Remaining qualification includes native Linux execution, exact hardware/firmware support, non-English Windows parsers, clean-machine checks, signing, and comparison against any newer NetworkHub source. Consult `VERIFICATION.md` for checks actually completed.
