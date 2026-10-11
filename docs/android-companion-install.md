# Android companion development build

The first snapshot APK compiled successfully in [Android CI run 38279028004](https://github.com/Floyd1551/Veilbreaker_Desktop/actions/runs/38279028004), from commit `cbd38f3`. JUnit serializer tests and Desktop validation of the Kotlin-generated capture passed. This verifies compilation and file compatibility, not physical-phone behavior.

## Install and capture

1. Obtain `app-debug.apk` from that run's `veilbreaker-android-debug` artifact, or the local copy `dist/Veilbreaker-Companion-0.1.0-dev.apk`.
2. Transfer the APK to your Android 10 or newer phone and open it. Android may require allowing installation from the file manager used to open this development APK.
3. Open **Veilbreaker Companion**, grant phone and precise-location permissions, and enable Android location services. Location permission is required for cellular information; this build does not record GPS coordinates.
4. Refresh SIMs, explicitly select the desired SIM, and capture a snapshot. Wait up to 15 seconds. Cached, incomplete, or empty results are possible with public Android APIs.
5. Select **Export capture JSON** and save the file through Android's document picker.
6. Copy the JSON to your computer using USB file transfer. In Desktop 0.29.0rc1 or newer, select **Diagnostics → Import Android capture**, review the observation and serving cell, then import it.

No USB debugging is required. This build captures public LTE/NR measurements, not the modem's entire decoded feed. Neighboring cells remain separate from serving cells. GPS and timed sessions are not implemented yet.

APK SHA-256: `63ba7fd14a86fc796fd96877b93e087332dcef4675463fd082810d259ca417af`.

## Device qualification still needed

Record the exact phone model, Android version, carrier, and returned LTE/NR fields. Check permission denial, location services disabled, SIM removal, stop/backgrounding, rotation, timeout, and export cancellation. Verify an actual phone export imports into Desktop. Do not publish personal capture files as test fixtures.

The APK is debug-signed. CI builds may use different debug keys, so a later development APK may require uninstalling the previous one; export captures before uninstalling. Stable release signing remains future work.
