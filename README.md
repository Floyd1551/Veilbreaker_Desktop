# Veilbreaker Desktop + CLI

An explainable field diagnostic workspace for Windows and Linux, rebuilt from the recovered **0.9.3 multimodem** source. Version **0.10.1rc1** adds a native desktop interface, packaging, persistent per-user storage, Unicode-safe exports, and saved-run comparison while retaining the CLI.

## Windows installation

Run `Veilbreaker-0.10.1rc1-Setup-x64.exe` from `dist`. Setup installs for your account, adds a Start menu shortcut, optionally adds a desktop shortcut, and registers an uninstaller. Python and administrator rights are not required. The installer is unsigned.

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
