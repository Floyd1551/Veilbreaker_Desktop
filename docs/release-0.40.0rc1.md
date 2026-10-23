# 0.40.0rc1 — guided field survey flow

Survey details now lead with the next unrun point, selected collectors, progress,
and manual versus batch behavior. Check next point readiness uses the settings
saved with that point, not unrelated selections currently shown in Diagnostics.
Checks run in a worker and display inline. They do not acquire telemetry, probe
devices or prove connectivity, and missing prerequisites do not impose a new gate.

Readiness results are invalidated when the point, settings or survey changes.
Outdated worker responses are discarded. Capture one point and pause, or capture
remaining points, follows the survey's existing manual/batch setting. Attempted
tests are never automatically repeated. Completed surveys require reopening.

Review latest attempted point selects its result and notes. Successful/partial
results open through the existing diagnostic viewer; failed points retain their
error. Survey detail reloads after worker completion/cancellation so interrupted
or failed results are available without reopening the survey.

Phone diagnostics still use Diagnostics followed by Add existing diagnostics.
This release does not add live phone sessions to survey queues or claim that
laptop network traffic measures a phone's cellular connection. Existing reports,
maps, comparison, exports and evidence formats remain compatible. Companion 0.5.1
requires no update for this desktop workflow.

Regression coverage includes point-setting precedence, legacy snapshots, missing
settings, changed-context rejection, completed states, real-worker delivery,
manual/batch labels, failed-point review, cancellation cleanup and narrow layouts.
Physical device qualification remains separate from automated checks.
