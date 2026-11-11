# Veilbreaker Mobile 0.8.19 development build

Android 10/API 29 or newer. Public LTE/NR and, when reported, GSM/WCDMA/TD-SCDMA/CDMA cell snapshots and bounded foreground USB sessions, with explicit SIM selection and user permissions. Optional phone location capture; no raw modem feed. Desktop analysis currently accepts only LTE/NR serving cells; legacy cells remain reference evidence.

The unified app retains the companion's application ID and USB capture
contract, and includes a standalone read-only Wi-Fi view based on capabilities in
the recovered Veilbreaker Mobile project. The Wi-Fi view reads connected-network
details and cached nearby observations when Android exposes them; it does not
start a scan, export Wi-Fi data, or send Wi-Fi observations to Desktop. Stop a
USB session before opening it. See [the consolidation plan](../docs/android-mobile-unification.md)
for remaining migration and reporting work.

Live, Diagnose, Survey, Reports and Tools pages remain inside the same foreground
workspace. Tools offers 38 searchable offline engineering calculators, two
additional two-way converters, 53 reference entries and 10 field guides.
Calculated worksheets can be copied with inputs, results and limitations.
Selected calculators include schematic diagrams and a calculated input/output
worksheet. Reference entries provide illustrated channel examples and quick
tables where applicable; guides have workflow figures and decision-cue tables.
All illustrations and tabulated examples are offline reference material, not
captured or calibrated measurements.
The Planning tab includes an idealized Wi-Fi AP count and geometry schematic, a
candidate FWA bearing and free-space path estimate with a manual trial comparison,
and an interactive operator-drawn network topology. These are
initial planning aids, not a site-specific coverage prediction, measured line of
sight, or network discovery. Wi-Fi and FWA planning inputs can be explicitly
saved and loaded on the phone. The interactive topology supports one explicitly
saved operator sketch, with confirmation before replacing or deleting the draft;
tuning comparisons remain session-only. Entered and calculated values are not
saved as measurement evidence.
FWA comparisons can include explicitly selected past cellular observations and
show original values and provenance; incompatible known cell contexts suppress
cellular deltas.

Tools also offers an optional, user-initiated OpenCellID lookup. Enter an
OpenCellID account key and a cell's radio, MCC, MNC, LAC/TAC and cell ID. A user
can explicitly select a complete registered identity from the last saved capture
to fill the form; selection does not perform a lookup. The
app sends those identifiers and the key over HTTPS only when Look up is pressed.
The provider receives the network IP address. You can explicitly save a key on
the phone using Android Keystore-backed encryption or use it for one lookup;
no GPS coordinates or measurements are sent. OpenCellID results are community-derived
cell-position estimates, not verified tower or serving-antenna locations; missing
results do not imply an absence of service. OpenCellID account terms, request
limits, and CC BY-SA 4.0 attribution apply. No credential is bundled.
After a successful lookup, the operator can explicitly send the candidate
coordinates to FWA planning after confirming replacement of the candidate-site
fields. Explicitly saved FWA inputs retain the candidate's source, identity,
retrieval time and reported sample/range metadata; editing either candidate
coordinate removes that attribution. Older drafts have no retained source.

The Cellular workspace offers capture readiness, a direct capture action and a
shortcut to review the latest saved capture. The live monitor also offers a
separate snapshot action; taking a snapshot stops the transient live monitor.
Expandable offline explanations for RSRP, RSRQ and SINR include field-use notes,
limitations and source information.
Capturing replaces the latest phone
capture, so export earlier evidence when needed. Live offers a direct input-configuration
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

Diagnose → Cellular includes an explicitly started, foreground-only live monitor.
Android may return cached samples; each response shows its modem age at receipt.
The monitor also shows time since the response and clears transient details when
monitoring stops; this elapsed time is not a new modem measurement.
The view stops after five minutes, when leaving the screen, on SIM changes, or
when other collection begins. It never saves evidence. Survey point review shows
recorded metrics and location provenance individually without averaging them.
A capture requested with location but without a usable fix is marked partial.

The live cellular monitor includes a short foreground-only trend for distinct,
recent samples of one fully identified LTE/NR serving cell. It clears on ambiguity,
cell changes, gaps or stop; it is not saved. Cached Wi-Fi cards show Android-reported
channel width and advertised security capabilities when available, not a security
audit. Mobile survey points support separately labeled operator observations.
Standalone cellular and GPS captures wait up to 30 seconds for a requested GPS fix;
cell response and location times are distinct, and missing location is partial.

The survey screen keeps primary point actions visible, with completion, export,
and deletion under More survey actions. GPS map controls are grouped around the
map; operator-supplied image settings are available on demand.

A PNG with no EXIF orientation metadata can be used when the operator supplies
a north-up image; declared rotated, mirrored or undefined orientations remain
unsupported. The app does not verify image orientation or geographic bounds.
