# Phone Location and Survey Inputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended here) or superpowers:subagent-driven-development to implement this plan task-by-task. Track completion with checkboxes and an execution ledger.

**Goal:** Collect opted-in phone location and cellular evidence across survey points using one foreground USB approval, with reliable source/time/accuracy reporting.

**Architecture:** Separate connection authorization from capture sessions on Android; reuse the existing capture envelope's optional location object. Desktop keeps equipment credentials in memory and passes them only to a bounded worker invocation, while journals store non-secret equipment configuration. A shared location presentation module serves diagnostic and survey reports and CSV exports.

**Tech Stack:** Kotlin Android framework APIs (API 29+), Python, PySide6, existing ADB loopback protocol, SQLite/JSON journals, JUnit and unittest.

**Spec:** docs/superpowers/specs/2026-10-16-phone-location-surveys-design.md

## Global constraints
- Capture lasts 5–300 seconds; cellular requests remain at least five seconds apart.
- Location recording is explicitly opted in, independent of permission used for cell access.
- Foreground only; no Wi-Fi listener, background tracking, map tiles, geocoding or transmission.
- Connection reuse expires after 15 idle minutes or 60 total minutes, and on Stop, backgrounding, authorization loss, Desktop exit or device change.
- Preserve old v1 captures and single-test companion compatibility; never persist credentials in journals, templates, reports or retry settings.
- Location labels use actual age/accuracy. Older than 10 seconds is Old fix; accuracy greater than 25 metres is Low accuracy. Missing coordinates/accuracy remain unknown.
- Retain all observations. The point position is the first qualified fix, never an invented average.
- USB GNSS gets a compatible data interface, not a working device option or unsupported qualification claim.

## Review focus
- A delayed callback from point A arrives during point B: reject by capture generation (tasks 1–2).
- Location denied or no SIM: independent source choices still collect available evidence (tasks 1 and 4).
- USB unplugged between points: preserve finished evidence and require reconnect (tasks 3–4).
- App restarts with a saved equipment selection: no stored credential and no silent acquisition (task 4).
- Mock, stale or unknown-age fix: preserved but never chosen as qualified point position (task 5).

### Task 1: Opt-in location capture and validated location-only observations

**Files:** Create android-companion/app/src/main/java/com/veilbreaker/companion/PhoneLocation.kt and LocationEvidence.kt; modify MainActivity.kt and CaptureSerializer.kt in that directory. Create companion LocationEvidenceTest.kt and tests/test_phone_location.py; modify src/veilbreaker/android_capture.py and docs/android-capture-v1.md.

**Interfaces:** LocationEvidence.serialize(fix fields, receiptElapsedMs) returns a location JSONObject matching the existing validator with optional fix_elapsed_realtime_ms and association metadata. PhoneLocation.start()/stop()/atReceipt(receiptElapsedMs) owns Android provider updates; its callbacks are generation-bound. An optional collection input-selection object records cellular/location booleans. A location-only subscription has key location-only and kind location_only; cells is empty and serving-cell selection is bypassed only for that explicit mode.

- [ ] Add failing Kotlin tests for opt-out, null/invalid accuracy, future monotonic fix time, altitude reference, mock flags and association age; add Python tests for legacy acceptance and explicit location-only validation.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p test_phone_location.py`; confirm intended failures. Run Android testDebugUnitTest in the configured Android CI for the failing contract fixtures when local Gradle/SDK is unavailable.
- [ ] Implement framework provider capture without Play Services. Prefer GNSS, label provider provenance, retain unavailable/permission states and independent no-SIM behavior. Location sampling is active only during a capture; the toggle is locked during it. Timestamp at callback receipt and attach only a fix already received, without delaying cellular callbacks waiting for GPS.
- [ ] Verify permission revocation/background/Stop removes updates; generation checks discard late callbacks. Run focused tests, validate Kotlin-produced fixtures with Desktop, and commit.

### Task 2: Reusable foreground connection, isolated capture sessions

**Files:** Create companion UsbConnection.kt and UsbConnectionTest.kt; modify UsbSession.kt, UsbPairing.kt, MainActivity.kt and LoopbackEndpoint.kt.

**Interfaces:** UsbConnection owns credential, connection ID, capabilities and expiry; command(name, token, body) routes to an isolated UsbSession. Start returns a new capture session ID each time; sample/status/stop require that ID. Pair requests optionally specify survey mode, displayed in phone approval. Responses advertise reusable_sessions and location capability flags without changing legacy protocol-1 required fields.

- [ ] Add failing JUnit cases for two sequential sessions with distinct IDs/buffers, stale/duplicate requests, overlapping starts, late callback generation, exactly 15-minute idle/60-minute total expiry, background revocation and single-use mode.
- [ ] Implement connection expiry independently of each 5–300-second session. Reuse applies only when explicitly approved for survey mode. Stop capture and revoke connection are distinct commands; foreground exit revokes both.
- [ ] Keep completed captures immutable; terminal callbacks cannot mutate the next session. Update endpoint allowlist and return explicit capability/version errors rather than permissive fallback.
- [ ] Run testDebugUnitTest and assembleDebug in Android CI, validate legacy/new response fixtures with Desktop, and commit.

### Task 3: Desktop capability negotiation and transient reusable credentials

**Files:** Modify src/veilbreaker/android_usb.py, android_usb_ui.py and tests/test_android_usb.py; create tests/test_survey_phone_input.py.

**Interfaces:** Add pair_connection(adb_path, serial, show_code, cancelled, survey_mode=False) -> dict containing token and capability metadata. Retain pair_device compatibility wrapper. collect_session accepts explicit cellular/location selection and optional connection identity, returning one capture envelope. revoke_connection(connection) performs bounded best-effort cleanup of that selected device only.

- [ ] Add failing tests for advertised capabilities, old-companion single-test fallback, survey reuse rejection on old companions, unique session IDs, cancellation/disconnect and owned-forward cleanup.
- [ ] Implement additive negotiation and UI labels for phone-approved location/cellular availability; reject mismatched requested capability. Never silently substitute a different connected device or turn on location from Desktop.
- [ ] Replace old token-entry error text with reconnect guidance. Keep credentials out of exceptions and progress; preserve partial results and single-test behavior.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p test_android_usb.py` and test_survey_phone_input.py; require passing results and commit.

### Task 4: Survey equipment selection and per-point worker dispatch

**Files:** Modify src/veilbreaker/survey_ui.py, survey.py, gui.py and jobs.py; extend tests/test_survey_phone_input.py, test_survey_lifecycle.py and test_gui.py.

**Interfaces:** SurveyPage holds an in-memory connection scoped to the selected survey. Journals store equipment with cellular/location choices, device identity and duration only. resume_survey gains a transient equipment argument; _run_session forwards a per-test android_live request to VeilbreakerApplication.run. Location-only prepare_live_input produces location evidence without missing-cell/RF diagnostics.

- [ ] Add failing tests for select-once/two-points acquisition, no capture on Configure/Add, independent source choices, no-SIM location-only runs, disconnect between points, and reconnect after restart.
- [ ] Add equipment controls and readiness on survey detail. Acquire phone approval explicitly for that survey, preserve non-secret settings per step, and block Run next when required equipment needs reconnection. Missing GPS fixes do not block a ready capture.
- [ ] Extend worker request handling and cancellation to survey captures. Remove short-lived request credentials after load as for standalone USB. Ensure automatic progression never exceeds the phone connection/capture limits; completed survey, switching survey, Desktop exit and explicit disconnect revoke the connection.
- [ ] Assert a sentinel credential is absent from journals, settings snapshots, templates, reports, evidence ZIP, errors and retry metadata. Existing saved-input and standalone diagnostics remain valid. Run focused tests and commit.

### Task 5: Shared location qualification, report tables and CSV

**Files:** Create src/veilbreaker/location_report.py and tests/test_location_report.py; modify cellular_report.py, survey_report.py, core.py, gui.py, report_viewer.py and survey.py.

**Interfaces:** qualify_location(location: dict | None) -> dict reports status, labels, reasons and qualified bool. location_rows(envelope: dict) -> list[dict] preserves observation-level source, coordinates, fix/receipt timestamps, sample ages and association offset. representative_fix(rows) -> dict | None returns first qualified fix. location_html(rows) and location_csv(rows) render shared rows.

- [ ] Add failing tests for exact 10-second/25-metre boundaries, missing accuracy, mock fixes, unknown ages, different altitude references, provider switches, movement/multiple fixes and first-qualified selection.
- [ ] Compute timing association only from same-phone monotonic fields. For multiple serving cells retain per-cell timing offsets rather than implying one shared modem timestamp. Qualify availability and timing separately; do not replace unavailable coordinates with zeros.
- [ ] Render in-app and HTML Location sections and per-point survey status/position; export location.csv with formula-safe text cells and original units. Preserve source evidence and identify captures with multiple distinct fixes; do not infer movement from ordinary GPS jitter.
- [ ] Run test_location_report.py plus survey/cellular/report-viewer tests. Inspect populated/no-fix/old-fix reports at small window sizes and commit.

### Task 6: Qualification, packaging and release

**Files:** Update docs/android-companion-install.md, docs/android-capture-v1.md, docs/field-workflows.md, docs/ROADMAP.md, Desktop/companion version files, and the execution ledger.

- [ ] Document phone opt-in, source selection, foreground/expiry limits, location quality and old-companion fallback. Correct outdated no-location text throughout app/setup docs.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests`; require zero failures. Android CI must pass unit tests, assembleDebug and Desktop validation of generated capture fixtures.
- [ ] Obtain one independent whole-branch review, address important findings, and rerun affected checks.
- [ ] Run `.venv/Scripts/python.exe tools/build_release.py` and `./build-installer.ps1 -SkipBuild`; require successful frozen checks and installer. Download and verify the matching CI APK artifact.
- [ ] Perform physical Samsung opt-in, multi-point, no-fix and disconnect checks when the device/user approval is available; otherwise clearly report these as outstanding without delaying verified artifacts.
- [ ] Commit/push verified source and provide installer/APK links, compatibility notes and validation limits. No USB GNSS hardware qualification is claimed.

## Execution recommendation
Native execution in this session: these tasks share session, callback and credential-lifetime interfaces, so one implementer minimizes handoff overhead. Use one fresh reviewer after integration. Approval of this plan is required before product changes under the writing-plans workflow.
