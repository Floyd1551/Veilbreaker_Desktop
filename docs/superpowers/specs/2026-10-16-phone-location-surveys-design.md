# Phone location and reusable survey inputs

Status: Direction approved; written design awaiting review.

## Purpose and scope

Use available equipment first: an Android phone can supply both cellular observations and location, while a later USB GNSS adapter can provide location independently. Implement opt-in phone location, location-aware reports, and reusable phone input for up to 20 survey tests. Preserve existing standalone snapshots and USB diagnostics. Do not require a map or an external receiver to conduct a survey.

This is architectural because the present USB session is single-use, and survey settings are persisted while phone credentials must remain transient. The existing observation.location structure supplies a compatible foundation.

## Operator workflow

Companion adds an unchecked Record location option with a visible state: Off, Waiting for fix, Ready, Old fix, Low accuracy, or Permission unavailable. Its location choice and selected SIM are fixed during a test. Permission to inspect cell information does not silently opt the user into recording coordinates. Collection remains foreground-only; stop, disconnect, backgrounding, or expiry releases location updates.

Survey details adds Equipment: cellular input (None or selected Android phone), location input (None or the connected phone), and existing spectrum settings. Show supported versus unavailable capabilities. USB GNSS is described as a future adapter, not offered as a working device. The architecture must allow location without cellular capture; a phone with no active SIM can still provide an opted-in fix using a location-only observation path.

Connect uses the existing authorized USB device selection and matching six-digit phone confirmation. In survey mode the phone explicitly approves reuse for this foreground survey connection. Run next starts one bounded capture; Add tests and Configure never start collection. Each test remains 5–300 seconds with cellular requests at least five seconds apart. Pause between points releases sampling and keeps only the approved connection ready. There is no background or Wi-Fi listener.

Connection approval expires after 15 idle minutes or 60 minutes total, or immediately on phone backgrounding, manual Stop, lost authorization, Desktop exit, or device change. Expiry requests reconnect; it never silently switches equipment. These limits apply to connection reuse, not to individual capture length. Existing single-test mode retains its current behavior.

## Location evidence

Retain the validated observation.location fields: status, source, provider, coordinates, horizontal accuracy, fix UTC, fix age, optional altitude with reference, vertical accuracy, speed, bearing, and mock indicator. Add optional monotonic fix timestamp and association metadata. Old captures without location remain valid. Do not create coordinates for unavailable fixes and do not substitute zero for missing accuracy.

Use Android framework location providers rather than introducing a Google Play Services dependency. Prefer an explicitly identified GNSS fix; where supported and selected, label a network-derived fix accurately. Never claim all phone locations are satellite fixes. If a provider cannot supply accuracy, retain an unavailable/unqualified result rather than inventing an estimate. Record provider changes as evidence.

At each phone observation, associate the latest fix received before that observation. Calculate fix age on the phone's monotonic clock; never subtract Desktop and phone monotonic timestamps. Record cellular sample age separately and the estimated timing difference between the modem sample and location fix when both timestamps are known. Location is associated evidence, not a claim that two sensors sampled simultaneously. A location-only observation uses an empty cells array and a location-only subscription descriptor; it bypasses serving-cell selection and RF analysis.

Default display policy: a fix older than 10 seconds is Old fix; horizontal accuracy greater than 25 metres is Low accuracy. Show the actual age and estimated accuracy beside the label. These are field-workflow thresholds, not a precision guarantee. Cached/mock/unknown-age fixes are explicitly marked. Preserve low-quality fixes for review but do not label them qualified. Missing location never prevents cellular or SDR collection. Manual point names and notes remain usable indoors.

## Session and storage design

Separate connection authorization from individual capture sessions. Each test receives a fresh session/capture identifier and isolated observation buffer. Reject stale session IDs, duplicate requests, overlapping captures, and late callbacks belonging to an earlier test. The phone displays the current connection and capture state. Desktop verifies capability/version before offering reusable mode; older companions retain single-test behavior.

Keep connection credentials only in application/worker memory and existing short-lived request transport. Never serialize tokens into survey journals, settings, templates, reports, retry records or logs. Save only non-secret equipment selection and acquisition settings per test. Resuming after application restart requires new pairing. Existing worker cleanup owns its ADB forwarding and retains partial evidence on interruption.

Every survey test saves its own raw phone envelope, location association and receiver provenance. Location source changes affect future tests and are recorded without rewriting earlier results. The common location record accepts phone, external_receiver and imported sources; a future USB GNSS adapter must populate that record and its own timing/quality metadata. Do not equate different devices' accuracy or altitude references.

## Reports and exports

Add a Location section to in-app and HTML reports, with source, coordinates, fix time, estimated accuracy, age, association offset, and qualification. Survey tables show each point's location status and selected representative fix: the first qualified fix in that point's capture, otherwise no qualified point position. Preserve all observations so movement is not reduced to a fabricated averaged coordinate. Clearly identify captures containing movement or multiple fixes without claiming a stationary survey point.

Export observation-level location CSV alongside existing evidence, retaining raw and qualified states. Reports retain manual point labels. No automatic tower locations, distance-based causal claims, geocoding, tiles, route tracking between tests, or heatmaps in this increment.

## Validation and delivery

Android tests cover opt-out, denied permission, no provider, no SIM location-only capture, old/low-accuracy/mock fixes, foreground cleanup, connection expiry, distinct repeated capture sessions and late callbacks. Desktop tests cover backward-compatible import, timestamp association, independent cellular/location selection, per-point provenance, partial disconnects, credential exclusion, and in-app/export agreement. Test old companion capability fallback and restored surveys requiring re-pairing.

Build Android in CI, validate generated fixtures with Desktop, run Desktop regression and frozen Windows checks, and produce an updated installer and APK. Physical Samsung testing remains separately reported; no USB GNSS device qualification is claimed without hardware. Push verified source to the user's repository.
