# Veilbreaker 0.35.0rc2

Fixes a desktop crash after clicking **Connect and use as input** for an Android
USB phone. The failure occurred during deferred Qt object cleanup after the
pairing worker completed, including unsuccessful connection attempts.

Pairing notifications now use explicit QObject slots instead of an anonymous
callback retaining the dialog. USB device selection and on-phone approval are
unchanged. No Companion update is required.

A process-isolated regression test exercises repeated successful, failed, and
cancelled connections through the desktop workflow, including garbage collection
and deferred worker destruction. The original implementation aborts in this test.

Also restores the bundled Qt WebChannel script's original line endings to match
its existing integrity manifest. Script behavior is unchanged.

Validation: 198 automated tests passed, plus 30 consecutive pairing cycles in the
native Windows UI. The user confirmed that the corrected desktop completed a full
diagnostic using the connected phone's data.
