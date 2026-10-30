# Veilbreaker Mobile 0.6 development build

Android 10/API 29 or newer. Public LTE/NR snapshots and bounded foreground USB sessions, with explicit SIM selection and user permissions. Optional phone location capture; no raw modem feed.

This first unified build retains the companion's application ID and USB capture
contract, and adds a standalone read-only Wi-Fi view based on capabilities in
the recovered Veilbreaker Mobile project. The Wi-Fi view reads connected-network
details and cached nearby observations when Android exposes them; it does not
start a scan, export Wi-Fi data, or send Wi-Fi observations to Desktop. Stop a
USB session before opening it. See [the consolidation plan](../docs/android-mobile-unification.md)
for remaining diagnostics, surveys, migration and reporting work.

[Setup and USB workflow](../docs/android-companion-install.md).

USB collection requires current platform-tools, an authorized USB debugging connection, explicit on-phone connection approval using a matching six-digit code (no token entry). The endpoint binds only to 127.0.0.1. Sessions last 5–300 seconds with requests at least five seconds apart. Foreground exit, stop, timeout and permission/SIM loss end collection. Completed observations remain locally exportable; cached sample ages are retained.

Build using JDK 17, Android SDK 35 and Gradle 8.9: `gradle testDebugUnitTest assembleDebug`. AGP 8.7.3/Kotlin 2.0.21 are pinned. The Android companion workflow builds the debug APK and validates both snapshot and session fixtures with Desktop's importer. No Gradle wrapper or stable release signing yet.

Physical Samsung qualification for this build, detailed legacy-radio fields and production signing remain future work. A passing build does not establish device compatibility. A different Android signing key can prevent an in-place upgrade; export saved captures before uninstalling an older app.

Readable previews now include connected/registered cells, neighbors and all observed band labels, with channel-derived candidates kept separate. See [cellular visibility release notes](../docs/release-0.39.0rc1.md).
