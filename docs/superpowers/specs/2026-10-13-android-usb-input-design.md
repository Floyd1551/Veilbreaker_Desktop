# Android USB input for diagnostic runs

## Approved intent
Use the phone as an input to an ordinary diagnostic test, alongside other selected collectors, rather than create a separate phone test. Retain source identity, timing, cached age and optional future GPS metadata.

## Delivered file-input stage
Desktop attaches an explicitly selected registered LTE/NR cell without running acquisition. Run diagnostic validates the source hash before collectors start, records phone measurements in a separate phone_ namespace, evaluates phone RF separately, and stores original JSON plus selection metadata in the same evidence bundle. Attachments remain visible until cleared; every reuse is explicitly labeled saved, not live. Existing standalone imports remain readable in history. Survey queue attachment is a subsequent UI integration; the initial attachment applies to Run diagnostic only.

## Proposed USB stage
Use Android Debug Bridge (ADB) as an explicit development transport. USB file transfer alone cannot command live collection. Desktop will locate a configured platform-tools installation, list authorized USB devices, and require explicit selection if multiple devices exist. The phone requires USB debugging and the user's on-device trust approval; Desktop must not approve trust prompts or select arbitrary devices.

The foreground companion will expose an explicitly armed capture session. User selects the subscription and arms the companion on the phone. Desktop requests carry unpredictable session/request identifiers. Responses must echo identifiers and include receipt timestamps. A request must not silently launch collection against a default SIM. Restrict the transport to the selected USB device and do not add a Wi-Fi listener.

A bounded collector requests updates no more frequently than every five seconds, for a user-selected duration capped at five minutes. Retain observations and modem sample ages, label repeated cached observations, and never invent a fresh timestamp for modem measurements. Complete collection with a terminal outcome. Permission revocation, disappearing subscription, disconnect, timeout, phone backgrounding, and Desktop cancellation stop further requests and preserve completed observations as partial evidence. Late responses cannot enter a later run.

Desktop stores the full session in the same diagnostic evidence bundle. RF session summaries include available samples, cached/unknown-age counts and per-cell changes; do not choose a strongest neighbor or blend different subscriptions/cells. Phone RF remains separate from computer throughput unless a later explicit link-verification feature establishes a shared path. GPS stays optional and absent until implemented.

## Verification and delivery
Fake-transport tests cover serial selection, bounded commands, disconnect, stale identifiers, cancellation, malformed data and partial sessions. Companion unit tests cover rate limits and session termination; CI must build the APK and validate exported session fixtures using Desktop. Physical Samsung validation is required for an end-to-end live claim. Deliver updated Desktop installer and companion APK with USB setup instructions; keep file attachment available when ADB is unavailable.

## Scope boundaries
No root, raw modem diagnostics, Wi-Fi server, background service, automatic permission grant, driver installation or automatic APK installation. ADB is a development transport; production USB transport and stable companion signing are separate work.
