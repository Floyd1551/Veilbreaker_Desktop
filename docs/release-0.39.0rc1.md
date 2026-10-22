# 0.39.0rc1 and Companion 0.5.0-dev — cellular visibility

Companion's readable capture preview and Desktop's cellular report now show:

- Connected/registered cells at the latest observation for each SIM, with primary,
  secondary, or unexposed roles explicitly labelled.
- Neighbor and unclassified observations, preserving cell/channel identity,
  exposed signal quantities, sample age and last-seen time.
- Bands observed across the capture, separated by SIM, radio, source and role.

Snapshots describe captured state, not the phone's current connection after the
capture ends. An empty latest observation clears the displayed connection. Old
neighbors remain labelled as earlier observations. Carrier names on neighbors
come only from that cell's identity; the serving SIM's carrier is never inherited.
Neighbor observations remain reference evidence and do not enter serving-cell
health scoring or tower matching.

Reported LTE/NR bands take precedence. When band labels are missing, the shared
offline downlink channel table supplies clearly labelled **channel-derived
candidates**. NR channel ranges overlap; multiple candidates remain visible.
Candidates are not confirmations, carrier identification, or a device capability
list. Unsupported/unknown channels remain unexposed. The reference is not exhaustive.

The numeric ranges are sourced from [AOSP AccessNetworkUtils](https://android.googlesource.com/platform/frameworks/base/+/master/telephony/java/android/telephony/AccessNetworkUtils.java),
retrieved October 22, 2026; its source SHA-256 is recorded in the shared asset.
All matching NR ranges are retained, including the documented n65/n66 overlap.
The explicitly identified LTE supplemental downlink ranges are included as
candidates rather than excluded as non-primary bands.

Android's [cell-info API](https://developer.android.com/reference/android/telephony/TelephonyManager#requestCellInfoUpdate(java.util.concurrent.Executor,%20android.telephony.TelephonyManager.CellInfoCallback))
can omit cells and rate-limit updates. [Reported NR bands](https://developer.android.com/reference/android/telephony/CellIdentityNr#getBands())
can be unavailable. These views expose the returned evidence; they do not unlock
Samsung's private modem diagnostics or perform an exhaustive all-band RF scan.

The existing capture limit remains 256 cell entries per observation; truncation
is now explicitly recorded in collection notes. Desktop's visibility inventory
and Companion's neighbor preview are bounded to 1024 groups, with omissions
identified. Raw captured observations remain in the exported evidence. Existing
raw capture contracts remain compatible; inferred bands never overwrite them.

The Windows installer and Companion APK must be updated separately. Companion
remains a development/debug build; physical Samsung qualification is separate
from synthetic unit tests and build checks.

## Qualification

- Desktop: 250 tests passed; the local Windows frozen release passed CLI,
  Unicode worker/evidence, six-page GUI, offline map, and terrain checks.
- Companion: all 16 Android tests passed, including four cellular-visibility
  tests; Kotlin-generated captures passed Desktop contract validation.
- The APK and Windows payload contain the same shared band-reference content.
- Regression coverage includes incomplete identities, latest connections after
  long captures, empty latest observations, and narrow Settings layout.
- Linux CI uses a virtual display with software rendering, Debian packages declare the required XCB
  keyboard libraries, and installer qualification selects the built version.

Build evidence: [Companion workflow](https://github.com/Floyd1551/Veilbreaker_Desktop/actions/runs/39830348606)
and [desktop packaging workflow](https://github.com/Floyd1551/Veilbreaker_Desktop/actions/runs/39831429402).
The desktop workflow link records the current CI outcome; local Windows checks
are separate from Linux and installer qualification.

## Samsung field check

Update Desktop and Companion separately, then collect a short live USB capture.
Compare the Companion preview with the Desktop cellular report: latest registered
cells, channels, exposed signal values and reported bands should agree. Neighbors
should appear separately, with age and last-seen information. A channel-derived
band is only a candidate. If the modem supplies no neighbors or no NR identity,
record that absence rather than interpreting it as proof those signals are absent.
Repeat after moving to a second survey point; retain both raw captures for comparison.
