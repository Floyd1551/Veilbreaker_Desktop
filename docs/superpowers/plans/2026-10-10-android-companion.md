# Android Companion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Produce foreground Android cellular captures that Desktop's validated v1 importer can review and analyze.

**Architecture:** A Kotlin collector reads public telephony APIs and serializes the established capture contract. A foreground activity owns permission requests, subscription selection, bounded sessions and document-picker exports. USB file transfer moves exports to Desktop; no network service, raw modem access or USB-debugging dependency is introduced.

**Tech Stack:** Kotlin, Android SDK (minimum API 29), Gradle wrapper, JUnit and Android instrumentation tests. Pin compatible build-tool versions after checking official Android documentation and available local tooling.

**Spec:** `docs/superpowers/specs/2026-10-10-android-cellular-design.md`; format: `docs/android-capture-v1.md`.

## Global constraints

- Public Android APIs only, no IMEI/IMSI/phone-number or message collection.
- Foreground capture only; no background location or monitoring service.
- Snapshot default; session request cadence at least five seconds, maximum five minutes.
- Preserve source subscription, cell roles, units, cached age and unavailable values.
- GPS collection is deferred; do not emit fake coordinates or require coordinates to export.
- Missing hardware/toolchain is reported rather than claiming a built or qualified APK.

## Review focus

- Permission revoked during collection: partial capture remains exportable.
- Default SIM changes: preserve selected subscription and stop if it disappears.
- Timeout or repeated cached callback: do not fabricate fresh measurements.
- Rotation/foreground exit: cancel collection and retain completed observations.
- Export cancellation: no recapture, data loss or changed sample timestamps.

## Task 1: Buildable companion and contract serializer

**Files:** create Android project in `android-companion/`, with `app/src/main/java/com/veilbreaker/companion/CaptureSerializer.kt` and matching unit tests. Build configuration and manifest belong to this deliverable.

**Interface:** `CaptureSerializer.encode(capture: Capture): String`; models mirror the v1 documented envelope and quantities.

- [ ] Verify SDK/JDK/build tools; pin a supported Gradle/Android plugin combination from official documentation.
- [ ] Write failing serializer tests for unavailable Android sentinel values, separate SS/CSI quantities, string cell IDs, UTC receipts and absent GPS.
- [ ] Implement models and serializer, including collection/subscription/permission metadata and all required fields.
- [ ] Run unit tests and pass the exported LTE/NR fixtures through Desktop `validate_capture`; build the APK before committing.

## Task 2: Foreground collector

**Files:** `CellularCollector.kt`, `CellularCollectorTest.kt`, API adapter and permission helpers in the same package.

**Interface:** `start(subscriptionId: Int, durationSeconds: Int, onObservation: (Observation) -> Unit, onComplete: (Outcome) -> Unit)`; `stop()` cancels pending callbacks and closes session state.

- [ ] Write failing fake-API tests for revoked permission, disappearing SIM, cached/future timestamps, callback timeout and cancellation.
- [ ] Implement per-subscription `requestCellInfoUpdate`, API guards for newer identity/signal fields and explicit unsupported/unreported values. Unsupported radio types remain typed reference cells.
- [ ] Enforce the five-second request interval, five-minute bound and foreground lifecycle. Compute modem age on the phone only; unknown/future timestamps yield null with a note.
- [ ] Run unit tests and capture-contract fixture validation. Commit without claiming physical-device qualification.

## Task 3: Capture, inspect and export UI

**Files:** `MainActivity.kt`, resources and instrumentation tests in `android-companion/app/src/`.

**Interface:** Activity presents collector state and calls serializer only on export; document-picker URI is the sole export destination.

- [ ] Add permission rationale, available-subscription selection, snapshot/session controls, stop, observation preview and export.
- [ ] Test cancellation of export, rotation/foreground exit and permission denial. Completed observations must remain available; exporting must never start acquisition.
- [ ] Build APK, inspect emulator behavior and import an exported fixture through Desktop history/report workflows. Record emulator limits.
- [ ] Document installation and USB file transfer. Qualify on the user's exact Samsung model/OS when connected; list actual returned fields and unsupported ones. No support claim based solely on emulator results.

Survey-point attachment follows validated companion-to-Desktop capture transfer as a separate increment.
