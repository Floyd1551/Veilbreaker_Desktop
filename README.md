# Veilbreaker Desktop + CLI

An explainable field diagnostic workspace for Windows and Linux, rebuilt from the recovered **0.9.3 multimodem** source. Version **0.27.1rc1** adds a native desktop interface, packaging, persistent per-user storage, Unicode-safe exports, and saved-run comparison while retaining the CLI.

## Windows installation

Run `Veilbreaker-0.27.1rc1-Setup-x64.exe` from `dist`. Setup installs for your account, adds a Start menu shortcut, optionally adds a desktop shortcut, and registers an uninstaller. Python and administrator rights are not required. The installer is unsigned.

The portable ZIP contains `VeilbreakerDesktop.exe`, the `veilbreaker.exe` CLI, and their shared `_internal` folder. Keep the whole folder together. Start with **Explore demo** for synthetic evidence; **Import metrics** analyzes a JSON snapshot without collecting live data.

The installed CLI is at `%LOCALAPPDATA%\Programs\Veilbreaker\veilbreaker.exe`. Setup does not change your PATH. Invoke that executable directly or add its directory to your user PATH.

## Development

Repository source lives in `src/veilbreaker`, with regression tests in `tests`, sample inputs in `examples`, build helpers in `tools`, and platform installers in `installer`. Architecture, reconstruction history, verification and the phased roadmap are in `docs`.

Generated `build`, `dist`, `test-artifacts`, and `.venv` directories stay local and are excluded from Git. Original recovery backups are archived outside the checkout. Local configuration, databases and captured evidence must not be committed. Build installers locally using the instructions below, or download artifacts from a successful GitHub Actions build; installer binaries are not stored in the source repository.

Requires Python 3.11+.

Windows:

```powershell
.\setup.ps1
.\run.ps1
.\.venv\Scripts\veilbreaker.exe selftest
```

Linux:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[desktop,build]'
.venv/bin/veilbreaker-desktop
.venv/bin/veilbreaker selftest
```

Use `pip install -e .` for CLI-only use. On Linux, Qt needs the system graphics/windowing libraries; the CI workflow records the Ubuntu runtime dependency installation. `ip`, `ping`, and optional `iw` supply native network measurements. GUI sessions need X11 or Wayland; offscreen mode is used only for automated verification.

## Workflows

- **Diagnostics:** site and scenario selection; optional ping/DNS, guided follow-up, cellular, Starlink, SDR and throughput collection. Review summaries, ranked hypotheses, supporting/contradicting evidence, findings, next tests, metrics and collector notes.
- **Import metrics:** analyze an existing JSON object and save its report/history without live collection.
- **Run history:** reopen the latest 200 runs and compare against the preceding run at the same site and scenario.
- **Tools & readiness:** dependency checks, serial-port listing, modem compatibility matrix and engine self-test.
- **SDR capture:** discover HackRF and capture three receive-only sweeps across 2400–2500 MHz. The Spectrum tab shows median/maximum traces from saved CSV evidence. RF amplifier and antenna power are off for this quick capture.
- **Settings:** edit the shared JSON configuration, hardware targets, adapter commands and storage location.
- **Evidence:** save ZIP bundles containing metric JSON, report JSON/text/HTML, collector notes and any recorded sweep evidence.

Long operations run in a separate cancellable process. Cancelling can leave partial artifacts; it does not mark a partial run as successful. Native cellular telemetry and Starlink operations are read-only, and HackRF support is receive-only. Active network tests generate traffic only when requested (or enabled by explicit CLI/configuration choices). Existing external JSON adapters remain executable commands under the current user.

## CLI examples

```sh
veilbreaker --help
veilbreaker init
veilbreaker doctor
veilbreaker platform-info
veilbreaker run --active --guided --site branch-01
veilbreaker analyze examples/cellular-degraded.json --json
veilbreaker history
veilbreaker compare BEFORE_RUN_ID AFTER_RUN_ID
veilbreaker modem list --json
veilbreaker modem drivers
veilbreaker modem status --port COM5 --driver auto
veilbreaker starlink status --json
veilbreaker sdr sweep --range wifi:2400:2500 --json
```

Use a Linux serial device such as `/dev/ttyUSB2` in place of `COM5` on Linux. Other retained commands include `baseline`, `case add/list`, `test pmtu/path`, `sdr info`, `modem probe`, and `starlink doctor`. Global `--config PATH` precedes the command.

## Data and upgrades

Fresh installations use `%LOCALAPPDATA%\Veilbreaker` on Windows and `${XDG_DATA_HOME:-~/.local/share}/veilbreaker` on Linux. Existing `~/.veilbreaker` storage is reused when it contains the old configuration or database. `VEILBREAKER_DATA_DIR` overrides this selection. An explicit `data_dir` in configuration determines database/evidence storage.

Config, SQLite history, cases and evidence are separate from application installation. Uninstall does not delete them. Back up the complete data directory with the app closed before upgrading. Configuration schema remains version 1. Diagnostic files are plaintext and can contain network identifiers, location when enabled, and adapter output; inspect bundles before sharing.

## Build and verify

```sh
python -m unittest discover -s tests -v
python tools/build_release.py
```

Build on each target OS. The build runs tests, creates both executables with shared libraries, exercises the frozen CLI and offline analysis worker, captures all five desktop pages, copies dependency notices, writes a build manifest, and emits an archive/checksum. On Windows, `build-installer.ps1` adds an Inno Setup 6 installer; `-SkipBuild` uses the already verified bundle. `tools/test-installer.ps1` checks the installer lifecycle in an isolated destination.

Linux builds include a per-user `installer/install-linux.sh`; run it from the extracted archive using `sh Veilbreaker/installer/install-linux.sh`. Where `dpkg-deb` is present, the build also creates a Debian package for system installation. Install with `sudo apt install ./Veilbreaker-*.deb`; remove with `sudo apt remove veilbreaker-desktop`. Linux CI targets Ubuntu 24.04 x64. Older glibc distributions and ARM require their own native builds and verification.

Remove a per-user Linux installation with `sh "${XDG_DATA_HOME:-$HOME/.local/share}/veilbreaker-app/installer/uninstall-linux.sh"`. Both Linux uninstall paths preserve diagnostic data. The build runs the per-user installation lifecycle in a temporary home; CI additionally installs and removes the Debian package. These checks still need a completed Linux run.

`requirements-build-windows.txt` records the exact Python dependency set used for the local Windows build; install it before the editable package when reproducing that environment. The build manifest records the actual runtime and installed packages for each artifact.

## Current qualification limits

Windows source, packaged-runtime and installer results are recorded in `docs/VERIFICATION.md`. Linux build automation is provided but Linux execution has not been verified on this Windows host. A real HackRF capture at 2400–2500 MHz has succeeded; broader band/firmware qualification and live modem/Starlink testing remain pending. Windows text-based ping/Wi-Fi fallbacks currently expect English output. `starlink_grpc` is an optional external Python integration; frozen packages use the separately installed `grpcurl` backend. External utilities and device drivers are not bundled. The GUI does not yet expose every advanced CLI command as a dedicated form.

HackRF host tools are found through `sdr.tools_dir`, `VEILBREAKER_HACKRF_DIR`, PATH, or common Windows Radioconda locations. Discovery does not change system PATH. The installed 2024.02.1 tools reported unknown board/firmware names on the tested device but completed capture; this is retained as a collector note. Spectrum levels are relative dB, not calibrated dBm, and a short energy sweep does not identify protocols or prove interference. Raw CSV, acquisition settings, tool log and summaries remain in the evidence bundle.

See [recovered feature inventory and architecture](docs/PROJECT_INVENTORY.md) and [next milestones](docs/ROADMAP.md). Original backup files remain untouched and are excluded from Git.

## Evidence integrity (0.10.1rc1)

New diagnostic bundles include `evidence-manifest.json` with SHA-256 hashes and run metadata. Use **Tools & readiness → Verify evidence ZIP** or `veilbreaker verify path/to/evidence.zip`. CLI exit codes: 0 verified, 1 failed, 2 legacy/unverified. Verification does not extract files and limits total uncompressed content to 512 MiB. The manifest detects file changes; it is not a digital signature or proof of measurement accuracy. Earlier bundles remain readable and are explicitly unverified.

See [the phased roadmap](docs/ROADMAP.md) for reliability, hardware workflows, guided investigations, platform qualification, and the later consumer interface redesign.


## Collection outcomes (0.10.2rc1)

The desktop displays live collector progress and a Collection tab with outcomes, durations, metric counts and notes. Metrics show their contributing collectors in acquisition order; the last source supplies the final value. Imported values are labeled `imported_metrics` rather than live hardware measurements.

New evidence includes versioned `collection.json`, covered by the integrity manifest. History reopens these details; older runs explicitly have no collection metadata. Required acquisition failures preserve available measurements and produce a partial collection summary. HackRF requires every configured range to return a sweep; throughput requires upload and download results. Optional GPS/Wi-Fi absence does not make the run partial. Collection completion does not imply healthy service, calibrated measurements, or complete hardware qualification.

`veilbreaker run` now returns **3** for a saved partial acquisition (including with `--json`). Its JSON report shape remains unchanged and its summary explains missing requested evidence. Review collector notes even when collection completes: individual collectors can return useful measurements alongside warnings. Cancellation still stops the worker without recording a successful completed run.


## Recovery and spectrum inspection (0.10.3rc1)

Acquisition checkpoints are written atomically before and after collectors. After cancelling a diagnostic or restarting following a crash, use **Tools & readiness → Recover interrupted captures**, then reopen the recovered run in History. CLI: `veilbreaker recover --config path/to/config.json` (omit `--config` for the default). Recovery skips live workers, never resumes traffic, preserves usable metrics and readable partial sweep CSVs, and labels the result interrupted. Repeating recovery does not duplicate history. Checkpoints created by older versions are unavailable; their raw artifacts remain untouched.

Reconnect your device, then choose **Retry after reconnect** to start a new diagnostic using the previous request and current settings. This rediscovers hardware and preserves the earlier run. Requested active tests run again only when you click Retry. After restarting the app, select the desired tests and run a new diagnostic. Missing measurement groups appear in Collection: cellular registration and signal, Starlink state/latency/loss, enabled network checks, both throughput directions, and each requested SDR range. Unsupported or missing measurements remain explicit rather than being treated as healthy results.

Spectrum now collapses setup controls to give the chart room. Use **Show run setup** to restore them, **Expand chart** for a separate maximized inspector, the mouse wheel or +/− buttons to zoom, drag or arrow keys to pan, and Reset/Home to show the full range. Hover shows frequency plus median/maximum relative power. Window sizing respects available desktop space; pages scroll when necessary and the Navigate menu remains available on smaller displays. Zoom magnifies existing bins; it does not increase the capture's frequency resolution. Change SDR bin width for finer acquisitions, subject to host-tool limits.


## Repeatable SDR workflows (0.11.0rc1)

In **Tools & readiness**, choose a 2.4 GHz (2400–2500 MHz), sub-1 GHz (600–1000 MHz), or 5 GHz (5150–5850 MHz) receive preset. Select 1–20 sweeps, 100/250/500/1000 kHz requested bins, and valid LNA/VGA gains. **Capture selected preset** uses those settings with RF amplifier and antenna power off; it does not rewrite your saved JSON configuration. The ordinary diagnostic SDR checkbox continues to use Settings. Capture metadata now records the discovered hardware serial.

To compare, open a saved run's **Spectrum** tab and choose **Compare saved capture**. Select another capture from the same site and frequency range as your before measurement. The inspector overlays before/after medians and shows changes in relative dB. Hover for individual bin values; save a JSON comparison containing all per-bin differences, run IDs, receiver settings and raw-file SHA-256 hashes.

Numeric comparison requires the same recorded hardware serial, range, frequency resolution, sweep count, gains and power settings, complete aligned frequency coverage, and successful capture metadata. Interrupted captures and unknown or mismatched settings are rejected. Keep antenna, cable and placement unchanged unless that change is the experiment. Differences do not identify protocols or prove interference; power remains uncalibrated. The comparison is a separate export and leaves original evidence untouched.


## Site survey sessions (0.16.0rc1)

**Site surveys** groups 1–20 named diagnostic runs under one survey name and site. On Diagnostics, choose the tests for a step. In Site surveys, enter a label and number of copies, then click **Add selected tests**. Change diagnostic flags and add more steps to mix test configurations. Remove unwanted steps before starting. The queue shows exactly which tests will run. SDR steps can use the current Tools receive preset; otherwise they use Settings. Site/scenario and receiver settings are held constant during the session.

Click **Run survey** to begin. By default, the desktop pauses after each test so you can move to the next point, select its row, save point notes, and explicitly continue. Uncheck the pause option for an uninterrupted batch. Each selected active/throughput test generates traffic again. GPS and mapping remain later work. Progress identifies the current step and collector. Each completed run retains its own report, collection status and evidence ZIP, linked by a stable survey/test ID.

Reopen a saved session to compare metrics side by side and open individual diagnostics. Missing measurements display as —, never zero. Exports include a survey JSON with observed-count/minimum/median/maximum numeric summaries, a comparison CSV, each available original evidence ZIP, and an integrity manifest. Different test selections or changed environmental conditions affect comparability; scalar SDR metrics are not substitutes for the stricter spectrum comparison tool.

Cancellation stops the worker and leaves completed results intact. The session shows interrupted/not-run steps when reopened. Tools → Recover interrupted captures can recover the active diagnostic, then reopen the survey to include it. It never automatically resumes traffic. Continue runs only unrun steps; completed, failed and interrupted steps are never repeated. Batch mode continues through failed steps; manual mode pauses after each attempt. Original settings are saved locally under `surveys/settings` and reused on continuation, even if current settings change. These settings snapshots are excluded from survey exports. Older sessions without a snapshot cannot be continued. Point-note edits retain a timestamped history and never rewrite original run evidence; re-export to include edits.

CLI examples:

```sh
veilbreaker --config config.json survey --plan examples/survey-plan.json --name "Antenna baseline" --manual
veilbreaker --config config.json survey --resume path/to/survey-ID.json
veilbreaker --config config.json survey --list
veilbreaker --config config.json survey --show path/to/survey-ID.json
veilbreaker --config config.json survey --export path/to/survey-ID.json
```

A plan is a JSON array of objects with `label`, optional `notes` (up to 2000 characters), and `options`. Supported boolean flags are active, guided, cellular, starlink, sdr and throughput. A completed partial session exits with code 3. Session journals are stored under the data directory's `surveys` folder; umbrella ZIPs are stored in `reports`.


### Reusable survey templates

In **Site surveys**, assemble the queue and choose the pause mode, then click **Save queue as template…**. On a later visit, use **Load template…**, review the queued tests and current site/scenario, targets and receiver settings, and click **Run survey**. Loading replaces the draft queue but never starts acquisition. Every start creates a new session and independent evidence.

Portable JSON templates preserve point labels, diagnostic selections and pause mode. They exclude prior results, point observations, run IDs, targets and device settings. Current Diagnostics/Settings and the current Tools preset selection apply when starting a visit; verify these when comparing visits. Existing saved sessions and their evidence are unaffected.


### Compare repeat visits (0.16.0rc1)

Open the current session in **Site surveys**, then choose **Compare this visit with a baseline…**. Select another saved visit for the same site. Points match by exact, unique label; queue order may differ. The table shows baseline/current values and signed numeric changes (current minus baseline). Export the comparison as JSON with survey and run references; original evidence stays unchanged.

Changes are withheld for incomplete collections, mismatched test selections/scenarios, or differing/unavailable original settings snapshots. Missing points and measurements stay explicit. A positive change is not automatically an improvement. Matching saved settings cannot verify identical antennas, device identity or environmental conditions; use the dedicated spectrum comparison for RF evidence. Older surveys without settings snapshots can still show values but do not get numeric changes.


### Everyday network settings (0.16.0rc1)

Settings now provides fields for the ping target, DNS test host, optional iperf3 server and port. Use hostnames or IP addresses, without URL prefixes or appended ports; IPv6 addresses are supported. Blank throughput server disables its configuration. Save network settings validates all fields before writing, preserves hardware/storage configuration, and never starts diagnostics.

Advanced configuration remains under **Show advanced configuration JSON** with its own save action. Save or reload unsaved advanced edits before using the network form. Saving or reloading advanced settings synchronizes the network fields. Site/scenario remain on Diagnostics; receive presets remain in Tools.


### Search saved history (0.16.0rc1)

**Run history** searches all saved runs by site, note, run ID, scenario or UTC date. Results use 200-run pages with Older/Newer controls and a matching count. Search is literal substring matching; percent signs, underscores and quotes are not wildcard or query operators. Clearing search restores all history. Changing pages or filters clears the selected run and stale comparison output.

**Compare selected to previous** finds the preceding run at the same site and scenario across the entire database, regardless of the current search or page. Equal timestamps use run ID as a stable tie-breaker. The spectrum comparison chooser remains independent of history search and uses the latest 200 runs for its site.

## GUI workflow improvements (0.17.0rc1)

The desktop adapts navigation and action rows to narrower windows. A workspace-wide task banner keeps collection progress and cancellation available across pages. Alt+1 through Alt+6 navigate pages; Ctrl+F focuses history search, or metric filtering while on Diagnostics. The Metrics tab filters names, values and contributing collectors without modifying captured evidence.

Settings groups Network, Cellular, Starlink and HackRF connection fields into tabs. **Save connection settings** validates and saves all form fields together without starting collection or changing the current investigation site. Acquisition ranges, gains, power settings, privacy choices and external adapter commands are preserved. **Advanced JSON** has a separate save action; unsaved edits in either editor are protected from the other editor's save. Reload restores saved configuration.

The diagnostic setup explains the selected measurements and targets, including active tests implied by guided follow-up. History and survey actions reflect selection/available work; empty history distinguishes no saved runs from no search matches.


### Confirmed cases (0.18.0rc1)

In **Run history**, select a saved run and open **Confirmed cases…**. Enter the verified cause and resolution, explicitly check that you verified the cause, then save. A diagnostic hypothesis alone is not confirmation. Confirmed cases may inform future suggestions through the existing similarity engine; original evidence is unchanged.

The window shows the latest 200 cases, including withdrawn records. Select a case to read its full cause and resolution. **Withdraw selected confirmation** excludes a mistaken case from future matching without deleting it or rewriting past reports. Open the window without a selected run to review existing cases only.


## Survey trends and field-workflow improvements — 0.19.0rc1

Open a saved survey and choose **Trends across visits…**. That survey is the baseline. Select an exact point label and numeric measurement to see observations across all saved visits for the same site, ordered by survey creation time. The plot uses equally spaced visits; the table provides UTC dates, values, baseline changes, collection states and exclusion reasons. Only complete observations with matching test selections, scenario and original settings contribute to the chart and minimum/median/maximum summaries. Missing, ambiguous and incompatible observations remain visible as gaps. A positive change is not automatically better. Receiver identity, antenna placement and environmental equivalence cannot be inferred from matching saved settings; use spectrum comparison for RF evidence.

Export trends as JSON (including run references, point notes, settings fingerprint and exclusions) or CSV. Original settings are not exported. The CLI offers the same offline analysis:

```powershell
veilbreaker --config config.json survey --trend path/to/baseline-survey.json --point "Roof" --metric latency_ms
```

Survey organization now includes search by name/site/point/ID/date, a session-state filter, and **Rename point**, **Move up**, and **Move down** controls for draft queues. Renaming enforces unique labels for reliable matching; removing and adding draft steps no longer generates duplicate labels. Draft editing does not change saved sessions or start tests. Save the edited queue as a template for subsequent visits.

Confirmed cases now support search, state filtering and paging across all records. Select a case to inspect its recorded events, open its source diagnostic, or export its record as JSON. New confirmations and withdrawals are recorded atomically with timestamped events; an optional withdrawal reason is retained. Repeated withdrawal does not duplicate events. Older cases remain usable with no fabricated event history. The additive case-event table preserves existing runs and case records. Exported cases are operator records, not independent proof of the diagnosis.


## Scenario guidance and SDR context — 0.20.0rc1

Diagnostics now explains each scenario beside the selector, including its actual thresholds and suggested collectors. Scenario names remain stable in saved configuration and history; choosing a scenario does not start tests.

Spectrum includes the supplied 154-entry offline U.S. reference with shaded bands, GNSS frequency markers and hover annotations. A smaller FCC-sourced reference is also selectable. **Band legend / import** searches expected uses and source URLs, imports custom CSV/JSON references, or restores either bundled reference. The selected reference is saved in the user data folder. Expanded and comparison charts use it too. This is a curated selection, not a complete allocation table, protocol detector, or transmit authorization.

The separate **SDR report** tab exports HTML and JSON with capture settings, source hashes, actual frequency coverage, strongest bin, estimated floor and observed-bin activity. New evidence bundles include these reports and the reference snapshot. Missing metadata and incomplete frequency coverage stay explicit. The activity estimate is not time occupancy; receiver settings, antenna and placement affect relative power.

See [band reference formats and sources](docs/band-reference.md). Reports can be generated from saved captures without connecting a receiver.


### 0.20.1rc1 — Advanced carrier reference

The base build now includes explicit general carrier associations and uplink/downlink/TDD direction for the supplied advanced reference. These appear in the searchable band legend, spectrum hover readout and SDR peak descriptions. Carrier associations are contextual and can include historical deployments; they do not identify a received transmitter. Existing custom selections are preserved: use **Band legend / import → Apply advanced U.S. plan** to switch to the bundled update.

This installer was built without rerunning tests at the user's request. Normal CI builds retain all checks.


### 0.20.2rc1 — Faster spectrum navigation

The band legend defaults to entries overlapping the loaded capture. Search carrier, direction or band, select a row, then choose **Zoom to selected band** (or double-click). Zoom stays within the captured frequencies and never starts acquisition. Center-frequency markers get a small inspection window, not an assumed signal bandwidth. Turn off **Only bands in the captured range** to browse the full reference. Local regression and installer tests were skipped under the requested resource constraint; normal GitHub CI remains enabled.


### 0.20.3rc1 — Ranked SDR observations

Each SDR range now reports its ten strongest observed bins, ranked by maximum relative power, with median power, median excess above the estimated floor, and carrier/direction reference context. Click a frequency in the in-app SDR report to inspect that location in the saved spectrum. HTML and JSON exports include the ranking; exported HTML is standalone without app-only links. Adjacent bins can represent the same signal, and this ranking does not identify transmitters. No new acquisition is started. Local test reruns remain skipped per the requested resource constraint.


### 0.21.0rc1 — Band-level site survey summaries

SDR reports summarize each overlapping reference band with general carrier/direction context, full-band frequency coverage, observed bin count, median bin power and maximum relative power. Click a band name to inspect its captured portion. Bands without resolved bin centers are marked explicitly. Center-frequency markers are excluded from these bandwidth summaries.

**Export band CSV** provides one row per band and capture range, including full-band and requested-overlap coverage, peak frequency, capture status, settings, source hash and reference version. New evidence ZIPs include `sdr_bands.csv`; HTML and JSON include the band summaries too. Overlapping reference bands reuse measurements and are not additive. Median bin power is not integrated band power. Compare captures only with compatible gain, resolution, antenna and placement; these relative values do not identify transmitters or prove interference. CSV rows are generated only for readable captures and overlapping reference bands; consult the full SDR report for missing evidence.

This local release was packaged without rerunning tests, following the earlier resource-saving instruction. CI remains enabled.


### 0.22.0rc1 — Desktop workflow polish

Diagnostics groups run configuration in a collapsible card and focuses on results after a run or import. **Configure next run** restores setup. Scenario purpose stays visible while detailed thresholds are available under **Scenario details**. Inactive cancel/retry actions are hidden; evidence export stays beside the displayed result.

Spectrum controls share a compact toolbar. The SDR report leads with site/run context and measurement summaries, uses proportional type, and offers **Show technical details and sources** without rereading capture files. HTML exports continue to include full metadata, limitations and sources.

Site surveys separate the plan from saved sessions, provide an empty-queue hint, reveal editing controls after adding points, and distinguish planning actions from **Run survey**. Active tasks remain cancellable through the global task banner.

Verification: visual review at 1280×800 and 1024×700, plus focused native UI interaction checks including 760px reflow. No live capture or full regression/installer lifecycle rerun was performed for this polish release.


### 0.23.0rc1 — Reports inside Veilbreaker

Use **View report** beside a diagnostic result or on a selected run in **Run history**. The offline viewer opens the saved diagnostic and SDR HTML reports directly from the evidence ZIP, with no browser or extraction step. If the ZIP is unavailable, a history entry can use its saved report directory.

Use **Run history → Open report…** to view standalone `.html`/`.htm` files or another evidence ZIP. Switch reports with the selector; use Find next / Ctrl+F and zoom controls to inspect them. **Save HTML** preserves the selected report's original bytes. HTML exports remain portable; PDF is not required for standalone use.

The viewer uses the existing bundled Qt text renderer, so there is no browser installation or online dependency. It displays text and tables; scripts, linked images/styles and external navigation are not loaded. Opening a report is separate from verifying evidence integrity; use the existing verification workflow when needed. Viewing limits: 8 MiB per HTML report, up to 20 reports and 16 MiB total HTML content per ZIP. No ZIP files are extracted.

Focused checks covered actual generated report rendering, standalone HTML, ZIP and directory loading, Unicode, report selection, and search. Full regression and installer lifecycle tests were not rerun for this release.

### 0.24.0rc1 — Site survey reports

Open a saved session in Site surveys and choose **View survey report / save HTML…**. The native viewer shows all points, collection states, assessments, saved operator notes, requested tests and measurement gaps. Save HTML from the viewer for sharing. Each newly exported survey evidence ZIP includes `survey_report.html` covered by its manifest. Older sessions can generate reports without repeating acquisition.

Numeric summaries use finite values from complete tests only, with observed/planned counts. Partial values remain in point details. Statistics are descriptive: mixed tests, settings and conditions do not establish comparability or improvement. Reports are snapshots of saved notes and results; reopening refreshes the snapshot.

### 0.25.0rc1 — Before/after survey investigation reports

In Site surveys, open a visit and choose Compare this visit with a baseline. Record the adjustment between visits; notes persist locally for that ordered visit pair. View the comparison report inside Veilbreaker and save HTML, or export JSON including the notes and timestamp. Reports separate measured changes (including zero changes) from unavailable comparisons with reasons, and retain survey/run references. Notes are operator annotations, not evidence of causation. Original evidence is unchanged.

### 0.26.0rc1 — Embedded SDR spectrum and waterfall

SDR reports now embed a median/maximum spectrum readout and capture-progression waterfall for each available range, inside the application and portable HTML. PNGs are self-contained and require no network, plotting library or browser. Frequency and relative-power scales are labeled. Gray waterfall cells mean no sample, not quiet spectrum. Rows represent CSV records, which may cover only part of a sweep; this is not a calibrated time axis. The waterfall displays the first 128 usable records with truncation labeled; the spectrum summarizes the full saved trace. Existing archived reports remain unchanged; reopen a saved diagnostic and export its SDR report to generate the new visuals.

### 0.27.0rc1 — Actionable follow-up guidance

Select a recommendation under Diagnostics → Next tests to read its purpose, procedure, expected observations, prerequisites and automation limits. Prepare supported test options selects only the relevant flags and reveals setup; acquisition starts only when you press Run. Preparation retains your current site, scenario and saved configuration. Settings and readiness shortcuts help review prerequisites. Unsupported recommendations remain manual, including matched SDR and path/MTU procedures. Repeated or simultaneous measurement recommendations clearly distinguish the single/sequential measurements Veilbreaker can prepare.

### 0.27.1rc1 — Reconstructed waterfall

Report waterfalls assemble CSV fragments into sweep rows using repeated frequency bins as boundaries. Newest displayed sweep is at the top. A taller dark heatmap, percentile contrast and embedded power legend replace the sparse record-strip image. Missing data stays dark gray; single-sweep and truncated captures are labeled. Timing is sweep progression, not calibrated elapsed time. Spectrum rendering is unchanged. Re-export an SDR report from its saved diagnostic to regenerate the waterfall; archived HTML is unchanged.
