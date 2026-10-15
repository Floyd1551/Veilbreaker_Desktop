# Android companion and live USB input

Desktop 0.32.0rc1 and Companion 0.3.0-dev support foreground USB cellular sessions as an input to an ordinary diagnostic run. This is development functionality; physical Samsung qualification remains outstanding. Only public Android LTE/NR data is available, not the entire decoded modem feed.

## Setup
1. Install Desktop 0.32.0rc1 and transfer/install `Veilbreaker-Companion-0.3.0-dev.apk` on Android 10 or newer.
2. Install current official [Android platform-tools](https://developer.android.com/tools/releases/platform-tools) on the computer. Desktop accepts the full path to `adb.exe` on Windows or `adb` on Linux. Platform-tools and phone USB drivers are not bundled.
3. Enable USB debugging in the phone's developer options, connect with a data-capable USB cable, and personally approve the computer's debugging authorization prompt on the phone.
4. Open Companion, grant phone and precise-location permissions, enable Android location services, refresh SIMs, and choose the desired SIM. GPS coordinates are not collected.
5. Tap **Connect to Veilbreaker**. Keep the app visible. The session stops when the app leaves the foreground.
6. In Desktop Diagnostics, choose **Live Android USB…**, enter the ADB executable path, refresh devices, explicitly select the authorized USB phone, and choose a duration of 5–300 seconds. Select **Connect and use as input**. Confirm that the six-digit code matches on Desktop and the phone, then approve on the phone. Nothing needs to be typed.
7. Select other diagnostic collectors as needed and press **Run diagnostic**. The phone collector requests updates at least five seconds apart. The run saves the complete phone session, per-cell ranges/changes and sample-age information with the other evidence.

Connect again for each new live test. A strong temporary credential is exchanged automatically after phone approval; it is not saved in settings or retry credentials. Confirmation expires after 60 seconds. The endpoint binds only to phone localhost and is reached through a temporary ADB forward; it does not listen on Wi-Fi. Turn off USB debugging when no longer needed.

## Cellular field report
Open the **Cellular** tab after a diagnostic. Each registered cell has carrier/SIM labels, reported band and cell identifiers, plus signal tables showing latest, minimum, median, maximum and change. Multi-sample captures include separate signal trends per cell. Missing values remain labeled Not exposed; cell identifiers do not establish a physical tower location. The report is also saved as `cellular_report.html` and embedded in the main HTML report.

## Results and stopping
Desktop keeps phone RF separate from the computer's throughput and modem measurements. It cannot assume those paths are the same connection. Cached readings remain identified by their modem sample age; a new request does not guarantee a fresh modem sample. Missing registered LTE/NR cells are explicitly reported.

Cancel requests cooperative shutdown and retains completed phone observations. Disconnects and timeouts produce partial evidence when data was already received. Closing Desktop waits for worker cleanup, with a bounded forced-stop fallback. The companion also enforces its own duration limit. The phone retains the last completed observations for manual JSON export.

## Saved-file fallback
Capture a snapshot, export JSON using Android's document picker and copy it to the computer. Choose **Attach Android input…**, select a registered LTE/NR cell, then **Run diagnostic**. The attachment remains visibly labeled saved until cleared. This method does not need USB debugging and still works without ADB.

## Troubleshooting
- No devices: check current platform-tools, data cable, USB driver, debugging and authorization. Offline/unauthorized devices cannot be selected. On Windows ADB versions without transport metadata, connect only one USB phone; the USB-only selector refuses ambiguous devices. Wi-Fi ADB and emulators are excluded.
- Rejected or expired pairing: stop and connect again on the phone, then configure a fresh live input in Desktop. Keep Companion visible.
- No cell data: confirm precise-location permission, Android location services and an active SIM. OEM/carrier APIs may omit fields or return cached/empty results.
- Development APK update rejected: CI debug keys may differ between builds. Export any capture first; uninstalling the old companion removes its local data. Stable production signing is not implemented.

## Validation status
Automated Desktop tests and Android CI cover the protocol, session boundaries, capture contract, evidence and UI paths. Actual USB transport, permissions and radio behavior on the user's phone still require an on-device check. No GPS, raw modem capture, background service or survey-queue phone attachment is included.
