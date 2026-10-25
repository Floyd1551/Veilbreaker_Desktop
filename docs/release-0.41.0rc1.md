# 0.41.0rc1 — live phone capture at survey points

In survey details, choose **Capture next point with phone…**. Select an authorized
USB device, approve the pairing code in Companion, and connect to capture that
point. Cellular observations and optional location follow the inputs selected on
the phone. Keep Companion visible during collection.

The capture runs after the point's saved desktop tests and saves its
report and original phone evidence directly under that point's run. Laptop network
tests still measure the laptop connection, not the phone's cellular data path.
The ordinary capture button retains its previous behavior and does not use the phone.

Phone capture always stops after one point, including in batch surveys. The next
point requires another explicit connection. The survey's manual/batch preference
is not changed. Pairing is tied to the point/settings reviewed before connection;
the worker checks that context under the survey lock before attempting collection.

Pairing tokens exist only in the existing transient worker request, which is removed
on worker startup, and process memory. They are not stored in survey settings,
templates, journals or retry requests. Nonsecret duration/input choices may be kept
with the point. Unexpected phone-run errors use a generic journal message to avoid
persisting credentials from exception text.

Cancellation uses the existing USB stop-and-save path. Captures interrupted after
observations arrive retain partial evidence; no observations means unavailable
evidence, not a successful phone capture. Completed, failed and interrupted points
are not automatically repeated, and completed surveys must first be reopened.

Companion 0.5.1 remains compatible; no phone update is needed. Automated tests use
synthetic captures and mocked USB transport; a real Samsung survey capture remains
a separate field qualification step.


Qualification: 267 source tests and frozen Windows CLI/worker/GUI/map/terrain checks
passed. The independent review found no actionable regressions; its seven non-GUI
phone tests passed, and all eight phone tests (including GUI dispatch) passed in
the project environment. Windows/Linux release and installer lifecycle checks passed in [run 40152222415](https://github.com/Floyd1551/Veilbreaker_Desktop/actions/runs/40152222415).

The local Windows installer compiled successfully and its SHA-256 sidecar was verified.
