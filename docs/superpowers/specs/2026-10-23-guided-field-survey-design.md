# Guided field survey detail screen

## Intent and scope

Make an existing survey easy to continue in the field: prepare the next point,
check its prerequisites, capture, review the result, then move to the next point
or compare/export. Retain the current desktop, survey journal and worker model.
This is a focused extension of the existing detail screen, not a new survey engine.

## Approaches

- **Integrated survey screen — selected by the user:** keep point results, notes
  and reports together; add a clear next-action area and survey-specific readiness.
- **Separate wizard:** stronger sequential guidance, but adds navigation and makes
  revisiting evidence harder during field work. Not selected.

## Screen behavior

At the top of survey details, show survey name/site, completed versus total tests,
the next unrun point and its selected collectors, plus manual/batch progression.
Use plain-language status and one prominent capture action. Keep the results table,
point notes, existing-diagnostic attachment, map, report and comparison controls.

- **Prepare:** explain which point/settings will run. Configuration remains in
  the existing survey configuration flow; changing global settings does not
  silently replace saved point settings.
- **Check readiness:** run the existing passive prerequisite checker in a worker,
  displaying results inside the survey. Check the next point's effective saved
  configuration and collector options, following the same precedence as execution.
  No telemetry acquisition, network test traffic or device opening occurs.
- **Capture:** manual surveys run the next point and pause; batch surveys continue
  the remaining queue. Button labels explicitly distinguish these behaviors.
  Retain current cancellation/recovery and never automatically rerun attempted tests.
- **Review:** after a result, make its diagnostic and point notes easy to reach.
  Partial, failed and interrupted results stay distinct from complete results.
- **Finish:** with no pending points, lead with reviewing the survey report and
  comparison/export actions. An open survey remains open until explicitly completed.
  A completed survey must be reopened before further capture.

## Readiness validity and limits

Readiness is a timestamped snapshot of prerequisites, not proof that a device is
connected or signal is available. Missing items are visible advice, not a new
mandatory capture gate. Invalidate the displayed check when the survey, next point,
or effective settings change; discard late worker results for a different context.
Disable duplicate checks/capture during active work. Missing legacy settings or
invalid survey state show a useful error rather than checking unrelated settings.

Live Android USB sessions are not currently queued survey inputs. Clearly state
this when describing available inputs; retain the supported workflow of capturing
a phone diagnostic and attaching it to the survey. Never imply laptop network tests
measure the phone's cellular link. No new pairing, GPS collection, thresholds,
automatic retry, export format or evidence schema is part of this slice.

## Implementation choices and acceptance

Builder choices: reuse PySide6 controls and current dark-teal styling, keep the
next-action area compact, and use a shared effective-settings helper if needed to
prevent execution/readiness drift. Existing survey and diagnostic files remain valid.

Verify saved-setting precedence, missing snapshots, manual/batch labels, stale
readiness results, completed/running states, partial result review, and narrow-window
layout. Run relevant survey/worker/GUI tests and release checks for changed code.
No physical phone or SDR qualification is implied by synthetic tests.
