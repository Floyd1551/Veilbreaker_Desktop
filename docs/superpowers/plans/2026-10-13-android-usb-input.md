# Android USB Input Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task after plan review. Steps use checkbox syntax for tracking.

**Goal:** Collect bounded foreground phone sessions over authorized USB and attach them to ordinary diagnostics.

**Architecture:** An armed companion session accepts identifier-bound requests over ADB-forwarded loopback transport. Desktop selects one authorized USB serial, validates responses and keeps partial evidence. The existing attached-input path stores and evaluates phone RF separately from desktop transport measurements.

**Tech Stack:** Kotlin Android public telephony APIs; Python subprocess and HTTP client; PySide6; Android platform-tools ADB; existing v1 JSON contract.

**Spec:** docs/superpowers/specs/2026-10-13-android-usb-input-design.md

## Global constraints
- Explicit phone SIM selection and arming; USB device authorization occurs on the phone.
- Requests no faster than five seconds; session duration at most five minutes.
- Foreground only; no Wi-Fi listener. Bind the phone endpoint to 127.0.0.1 only, accessible through an explicit ADB forward.
- Unpredictable session/request identifiers; maximum response size 16 MiB and bounded network/subprocess timeouts.
- Preserve raw observations, sample age, source and terminal outcomes; GPS absent unless actually collected in a future feature.
- No automatic permission grants, driver/APK installation, raw modem access or root.

## Review focus
- Two connected phones: never use an implicit/default serial (Task 2).
- Phone stops or rotates while request pending: reject late callbacks and retain completed observations (Task 1).
- A stale response from an earlier run: request/session mismatch must be rejected (Tasks 1–2).
- Disconnect midway: export completed observations and label partial (Tasks 2–3).
- Cached or changing serving cells: retain cell identity and age without inventing fresh measurements or blending cells (Task 3).

## Task 1: Armed foreground companion session
**Files:** android-companion/app/src/main/java/com/veilbreaker/companion/{MainActivity,CaptureSerializer}.kt; new UsbSession.kt and LoopbackEndpoint.kt; matching app/src/test Kotlin tests; AndroidManifest.xml.
**Interface:** UsbSession.arm(subscriptionId: Int, durationSeconds: Int): String returns a random token displayed on phone; start/request/stop messages contain token and request UUID. Status responses contain protocol version 1, matching identifiers, terminal outcome and v1 capture envelope. Token expires when disarmed or backgrounded. LoopbackEndpoint serves only on 127.0.0.1:8765; INTERNET permission permits loopback sockets, no remote network requests.
- [ ] Write tests rejecting duration outside 5..300 seconds, duplicate identifiers, wrong token, unarmed calls and requests less than five seconds apart; verify cancellation preserves observations and ignores late callbacks.
- [ ] Run tests and confirm failure before implementation.
- [ ] Extract bounded CellInfo acquisition from Activity into UsbSession, preserving explicit SIM, permissions and disappearance checks. Persist completed observations after every callback. Add Arm USB session/Stop controls and display the ephemeral token.
- [ ] Implement versioned JSON POST endpoints /start, /sample, /stop and GET /status with bounded body sizes and constant-time token checking. Close listener on foreground exit. Bind failures must leave manual snapshots usable.
- [ ] Run Kotlin unit tests, build APK in CI and pass a generated multi-observation session through Desktop validation. Commit.

## Task 2: Desktop ADB transport
**Files:** new src/veilbreaker/android_usb.py; tests/test_android_usb.py.
**Interface:** list_devices(adb_path) -> list of serial/state records; collect_session(adb_path, serial, token, duration_s, cancelled, progress) -> validated capture plus terminal outcome. Subprocess commands use argument arrays and explicit -s serial, never shell text. Reject non-USB/network serials and unauthorized/offline devices. Use adb forward tcp:0 tcp:8765; remove only the allocated forwarding rule in finally.
- [ ] Write fake-command/socket tests for no devices, multiple devices, unauthorized state, serial validation, response mismatch, malformed/oversize response, deadline, disconnect and cancellation; prove cleanup only removes the owned forward.
- [ ] Run tests to establish failures.
- [ ] Implement bounded polling, per-request UUID, five-second minimum cadence and five-minute deadline using monotonic time. Preserve last validated partial envelope if transport fails; no observations means an explicit failed collector, never fabricated data.
- [ ] Run tests on Windows-compatible command construction and POSIX paths. Commit.

## Task 3: Run integration and observation summaries
**Files:** src/veilbreaker/{core,android_import,gui,jobs}.py; new android_usb_ui.py; tests/test_android_import.py and test_android_usb.py.
**Interface:** run android_live option contains adb_path, explicit serial, duration_s and ephemeral token; never persist the token in config, evidence or retry history. Collector output stores full v1 capture and terminal status in the current run. Saved-file and live inputs are mutually exclusive.
- [ ] Write tests showing one run/evidence bundle, partial-session retention, no phone/host metric overwrite, token redaction and changed-cell/cached-age summaries.
- [ ] Run tests to confirm failures.
- [ ] Add device refresh/selection, duration and ephemeral token entry. Explain on-phone arming and USB authorization, show Live Android input in run plan and clear credentials after use. Collect session as one acquisition step; cancellation cooperatively saves partial data before process shutdown where possible.
- [ ] Summarize per-cell sample counts, known/unknown ages and repeated timestamps without combining different cell identities. Keep phone RF findings separate from desktop transport conclusions. Historical single-cell file selection continues to work.
- [ ] Run focused GUI/import/transport/evidence tests and packaged smoke checks. Commit.

## Task 4: Qualification and delivery
**Files:** docs/android-companion-install.md; docs/ROADMAP.md; version files and build artifacts.
- [ ] Produce new APK and Windows installer; record test scope honestly and preserve file attachment fallback.
- [ ] On an explicitly authorized connected phone, verify arming, a short session, stop, disconnect, backgrounding and Desktop report/evidence reopening. If hardware is absent, report that physical qualification remains outstanding.
- [ ] Update setup instructions and troubleshooting for adb missing, unauthorized/offline device, token expiry and no public cell information. Push source to GitHub.

Survey-queue attachment and stable production signing are separate follow-ups. This plan does not mark live USB complete until the transport, UI and companion all pass their applicable checks.
