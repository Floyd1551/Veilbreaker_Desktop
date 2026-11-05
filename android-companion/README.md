# Veilbreaker Mobile 0.8.4 development build

Android 10/API 29 or newer. Public LTE/NR and, when reported, GSM/WCDMA/TD-SCDMA/CDMA cell snapshots and bounded foreground USB sessions, with explicit SIM selection and user permissions. Optional phone location capture; no raw modem feed. Desktop analysis currently accepts only LTE/NR serving cells; legacy cells remain reference evidence.

The unified app retains the companion's application ID and USB capture
contract, and includes a standalone read-only Wi-Fi view based on capabilities in
the recovered Veilbreaker Mobile project. The Wi-Fi view reads connected-network
details and cached nearby observations when Android exposes them; it does not
start a scan, export Wi-Fi data, or send Wi-Fi observations to Desktop. Stop a
USB session before opening it. See [the consolidation plan](../docs/android-mobile-unification.md)
for remaining migration and reporting work.

Live, Diagnose, Survey, Reports and Tools pages remain inside the same foreground
workspace. Tools offers offline Wi-Fi channel/frequency and dBm/mW calculators
and a searchable wireless reference library. Entered and calculated values are
not saved as measurement evidence. Live offers a direct input-configuration
shortcut; SIM selection follows the subscription identity when the list changes. The optional network test sends one bounded HTTPS request to the
operator's chosen URL over an explicitly selected Android network; a short
download is an estimate, not a sustained capacity test. Upload, jitter and
packet loss are not measured. The app can group up to 20 explicitly added
captures into a phone-only survey and export that survey as JSON; a new capture
can also be collected and added directly from an open survey, with cancellation
and partial results clearly indicated; Desktop
survey import and migration from the older Mobile application are not yet
supported. Reports can export the most recent phone capture as PDF or JSON.

The cellular view shows gauges for captured serving-cell measurements and a
trend only when there are multiple distinct modem-receipt timestamps for the same
identified cell; timestamps do not guarantee fresh physical measurements. Wi-Fi cards show current connection information and nearby cached results,
including sample age when available. A per-band chart groups up to 500 cached
observations by their reported primary frequency; it does not trigger a scan or
infer channel width or utilization. The GPS view can show an explicitly started
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

Diagnose provides a selected-SIM public connection snapshot and a read-only network
interface inventory. A USB peripheral view lists Android-reported descriptors and
identifies a possible HackRF by USB ID; detection does not mean SDR capture is
supported. No USB peripheral is opened or controlled. Ethernet is visible only
when Android supports the adapter and exposes a network.

Reports can browse the latest captured serving and neighboring cells, filtered by
role or search, with timestamps, modem-reported and derived bands distinguished.
Wi-Fi inspection filters and sorts previously cached results without starting a
new scan; the frequency chart is not affected by the list filters.
