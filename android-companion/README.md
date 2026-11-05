# Veilbreaker Mobile 0.8.1 development build

Android 10/API 29 or newer. Public LTE/NR snapshots and bounded foreground USB sessions, with explicit SIM selection and user permissions. Optional phone location capture; no raw modem feed.

The unified app retains the companion's application ID and USB capture
contract, and includes a standalone read-only Wi-Fi view based on capabilities in
the recovered Veilbreaker Mobile project. The Wi-Fi view reads connected-network
details and cached nearby observations when Android exposes them; it does not
start a scan, export Wi-Fi data, or send Wi-Fi observations to Desktop. Stop a
USB session before opening it. See [the consolidation plan](../docs/android-mobile-unification.md)
for remaining migration and reporting work.

Live, Diagnose, Survey and Reports pages remain inside the same foreground
workspace. The optional network test sends one bounded HTTPS request to the
operator's chosen URL over an explicitly selected Android network; a short
download is an estimate, not a sustained capacity test. Upload, jitter and
packet loss are not measured. The app can group up to 20 explicitly added
captures into a phone-only survey and export that survey as JSON; Desktop
survey import and migration from the older Mobile application are not yet
supported. Reports can export the most recent phone capture as PDF or JSON.

The cellular view shows gauges for captured serving-cell measurements and a
trend only when there are multiple distinct modem-receipt timestamps for the same
identified cell; timestamps do not guarantee fresh physical measurements. Wi-Fi cards show current connection information and nearby cached results,
including sample age when available. The GPS view can show an explicitly started
foreground fix and locations from the last saved capture. It can overlay points on
a user-supplied, north-up Plate Carrée image with operator-entered WGS84 bounds;
an explicitly enabled OpenStreetMap street basemap is also available when online.
Tile requests disclose the approximate map area to the map provider; this is not
a downloadable offline map. The image workflow does not validate its bounds or
support Web Mercator images. Images with rotated or mirrored EXIF orientation are rejected. The
image and display do not modify recorded evidence. USB sessions must be stopped
before opening the GPS or Wi-Fi views.

[Setup and USB workflow](../docs/android-companion-install.md).

USB collection requires current platform-tools, an authorized USB debugging connection, explicit on-phone connection approval using a matching six-digit code (no token entry). The endpoint binds only to 127.0.0.1. Sessions last 5–300 seconds with requests at least five seconds apart. Foreground exit, stop, timeout and permission/SIM loss end collection. Completed observations remain locally exportable; cached sample ages are retained.

Build using JDK 17, Android SDK 35 and Gradle 8.9: `gradle testDebugUnitTest assembleDebug`. AGP 8.7.3/Kotlin 2.0.21 are pinned. The Android companion workflow builds the debug APK and validates both snapshot and session fixtures with Desktop's importer. No Gradle wrapper or stable release signing yet.

Physical Samsung qualification for this build, detailed legacy-radio fields and production signing remain future work. A passing build does not establish device compatibility. A different Android signing key can prevent an in-place upgrade; export saved captures before uninstalling an older app.

Readable previews now include connected/registered cells, neighbors and all observed band labels, with channel-derived candidates kept separate. See [cellular visibility release notes](../docs/release-0.39.0rc1.md).
