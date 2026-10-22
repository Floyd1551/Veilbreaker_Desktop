# Veilbreaker Android companion 0.5 development build

Android 10/API 29 or newer. Public LTE/NR snapshots and bounded foreground USB sessions, with explicit SIM selection and user permissions. Optional phone location capture; no raw modem feed.

[Setup and USB workflow](../docs/android-companion-install.md).

USB collection requires current platform-tools, an authorized USB debugging connection, explicit on-phone connection approval using a matching six-digit code (no token entry). The endpoint binds only to 127.0.0.1. Sessions last 5–300 seconds with requests at least five seconds apart. Foreground exit, stop, timeout and permission/SIM loss end collection. Completed observations remain locally exportable; cached sample ages are retained.

Build using JDK 17, Android SDK 35 and Gradle 8.9: `gradle testDebugUnitTest assembleDebug`. AGP 8.7.3/Kotlin 2.0.21 are pinned. The Android companion workflow builds the debug APK and validates both snapshot and session fixtures with Desktop's importer. No Gradle wrapper or stable release signing yet.

Physical Samsung qualification, detailed legacy-radio fields and production signing remain future work. A passing build does not establish device compatibility.

Readable previews now include connected/registered cells, neighbors and all observed band labels, with channel-derived candidates kept separate. See [cellular visibility release notes](../docs/release-0.39.0rc1.md).
