# Veilbreaker Android companion — development snapshot

Initial snapshot-only implementation for Android 10/API 29 and newer. This is not a qualified modem scanner or a raw baseband feed. Public Android APIs may return cached, incomplete or no measurements, especially on some 5G NSA devices.

## Implemented source

- Explicit SIM selection and phone/precise-location permission request.
- One bounded cell-info request with 15-second timeout; stop/backgrounding invalidates pending callbacks.
- LTE and NR identity/signal conversion, unavailable-value handling and modem sample age.
- Separate neighboring/serving roles, SS/CSI metrics and subscription-local data.
- Local last-capture persistence and document-picker JSON export. Export does not acquire new data.
- No GPS collection, network service, background permission, IMEI/IMSI or traffic capture.

Open the app, grant permissions, enable Android location services, refresh SIMs, choose a SIM and capture. Export JSON, transfer it using USB file transfer, then use **Diagnostics → Import Android capture** in Desktop 0.29.0rc1 or newer. No USB debugging is required for capture-file transfer. Optional GPS fields remain reserved for later work.

## Build

JDK 17, Android SDK platform 35 and Gradle 8.9. From this folder run `gradle testDebugUnitTest assembleDebug`. Android Gradle Plugin 8.7.3 and Kotlin 2.0.21 are pinned. A Gradle wrapper is not yet included; use the specified installed Gradle or the CI workflow.

The **Android companion** GitHub Actions workflow builds a debug-signed APK, executes serializer tests and validates a Kotlin-generated capture using Desktop's Python importer. Download its artifact only after that workflow succeeds. Debug signing is for development, not a stable production update/signing strategy.

The local development host did not have Java, Gradle or Android SDK available when this source was created. Local APK compilation, emulator testing and physical-device qualification have not been performed. Check CI for compilation results; source presence alone is not a successful build.

## Remaining work

- Verify compilation and contract tests; resolve any CI findings.
- Exercise permission denial/revocation, SIM removal, rotation, backgrounding, timeout and document-picker cancellation on emulator/device.
- Add timed sessions (at least five seconds between requests, maximum five minutes), fresh/cached deduplication and full lifecycle tests.
- Expand legacy-radio metrics; current non-LTE/NR entries retain type/registration/age but no detailed identity/signal fields.
- Qualify the exact Samsung model, Android version and carrier, and record returned/unavailable fields.
- Production signing, a reproducible Gradle wrapper, visual polish and survey-point attachment.

Build compatibility reference: https://developer.android.com/build/releases/agp-8-7-0-release-notes
