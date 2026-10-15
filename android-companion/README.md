# Veilbreaker Android companion 0.3 development build

Android 10/API 29 or newer. Public LTE/NR snapshots and bounded foreground USB sessions, with explicit SIM selection and user permissions. No raw modem feed or GPS collection.

[Setup and USB workflow](../docs/android-companion-install.md).

USB collection requires current platform-tools, an authorized USB debugging connection, explicit on-phone connection approval using a matching six-digit code (no token entry). The endpoint binds only to 127.0.0.1. Sessions last 5–300 seconds with requests at least five seconds apart. Foreground exit, stop, timeout and permission/SIM loss end collection. Completed observations remain locally exportable; cached sample ages are retained.

Build using JDK 17, Android SDK 35 and Gradle 8.9: `gradle testDebugUnitTest assembleDebug`. AGP 8.7.3/Kotlin 2.0.21 are pinned. The Android companion workflow builds the debug APK and validates both snapshot and session fixtures with Desktop's importer. No Gradle wrapper or stable release signing yet.

Physical Samsung qualification, detailed legacy-radio fields, production USB transport/signing, GPS and survey-point attachment remain future work. A passing build does not establish device compatibility.
