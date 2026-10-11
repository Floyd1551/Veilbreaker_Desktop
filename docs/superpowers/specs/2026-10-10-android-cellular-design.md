# Android cellular companion and Desktop import

Status: standard-first design approved; optional future GPS extension requested October 10, 2026. No Android compatibility claim or implementation is implied by this document.

## Intent

Use an ordinary Android phone as a cellular measurement source for Veilbreaker. Target broad Android compatibility, with the user's Samsung Note Ultra as the first physical qualification device once its exact model and Android version are available. Collect the public telemetry Android exposes, preserve the original observations, and make them usable in Desktop history, surveys and reports.

An ordinary app cannot obtain everything decoded internally by the modem. Raw baseband diagnostics, IQ samples, decoded traffic and vendor diagnostic interfaces are outside standard support. Device-specific adapters may follow only after their interfaces are identified. Wilson scanner support remains a separate task awaiting its model and export/protocol documentation.

## Delivery boundaries

1. Establish the versioned capture contract and strict Desktop importer, with synthetic fixtures and native review UI.
2. Build a foreground Android companion that records and exports this format. Transfer exported files by USB file transfer, then import locally into Desktop. This first transport requires neither a cloud service nor USB debugging.
3. Attach selected imported observations to named survey points and include original captures in evidence bundles. Preserve existing survey limits and comparison safeguards.
4. Qualify on the user's phone. Direct live USB control/streaming is a later transport increment, not claimed by file transfer. Tethered network tests and explicit interface binding remain separate roadmap work.

This specification covers stages 1–3; stage 4 requires the phone. Each stage must remain independently usable. Do not publish an Android installer until an APK has actually been built; emulator validation is not physical modem qualification.

## Companion behavior

Native Kotlin application under `android-companion/`, initially Android 10/API 29 or newer. Use public TelephonyManager, CellInfo and signal-strength APIs, with runtime guards for newer fields. Choose build-tool versions from official Android documentation when implementing and pin them in the project.

The flow is permission explanation → available subscription selection → snapshot or bounded session → inspect observations → export JSON using Android's document picker. Request only permissions needed by the selected public APIs, including phone state and precise location where required. Show permission denial, disabled location services, missing telephony hardware, no SIM, timeout and unavailable measurements as distinct outcomes. Do not require background location or run a background monitoring service.

Bounded sessions default to one snapshot; optional sessions request updates no more frequently than every five seconds, up to five minutes. Android controls actual update frequency. Stop cancels pending collection and retains completed observations. Exporting must not trigger a new measurement. Do not infer new observations from repeated cached results.

Capture LTE and NR identity and signal fields supported by the runtime: registration/connection role, MCC/MNC, cell identity, tracking area, PCI, EARFCN/NRARFCN, reported bands, bandwidth where available, LTE RSRP/RSRQ/RSSI/RSSNR/CQI/timing advance, NR SS and CSI measurements where reported. Keep secondary and neighboring cells separate. Other public CellInfo radio types are retained as typed observations when supported by the companion implementation, with unsupported types explicitly listed.

Do not query IMEI, IMSI, phone numbers, message content or call records. Device context is manufacturer, model, Android/API version and companion version; subscription selection uses an export-local identifier rather than persistent subscriber identity. GPS coordinates are not required for this phase.

## Capture contract version 1

UTF-8 JSON envelope:

- `format`: literal `veilbreaker.android.cellular`.
- `schema_version`: integer `1`.
- `capture_id`: UUID; `created_utc`: ISO 8601 UTC timestamp.
- `device`: manufacturer, model, Android version, API level and companion version.
- `collection`: requested mode, start/end UTC, outcome (`complete`, `partial`, `cancelled`, `failed`), permission state and structured notes.
- `subscriptions`: export-local subscription keys and available radio context; distinguish unknown from absent.
- `observations`: ordered snapshots, each with observation ID, subscription key, receipt UTC and elapsed-realtime milliseconds, acquisition outcome and cell list.
- Each cell records radio type, registered flag, connection status, modem observation age when calculable, typed identity fields and explicitly named signal quantities with units.
- Unavailable fields use null with a reason (`not_reported`, `unsupported_api`, `permission_denied`, `timeout`, `unknown`). Android sentinel integers must never be normalized into real measurements.

LTE RSSNR stays distinct from NR SS-SINR and CSI-SINR. Band lists are device-reported; any later channel-derived band must carry a separate derived label. An empty NR list or a 5G status icon does not establish absence or presence of a measurable NR serving leg. Preserve all returned cells without selecting the strongest neighbor as the serving cell.

Keep original modem monotonic timestamps separate from receipt wall-clock time. Compute age only on the phone within the same boot's clock domain; future/invalid ages are unknown. Desktop must not compare its monotonic clock with the phone's. Cached readings retain their ages and are labeled; repeated timestamps are not fresh samples.

Bounds: 16 MiB input, 1,000 observations and 256 cells per observation. Reject invalid envelopes, excessive collections, duplicate IDs, nonfinite numbers and unexpected types before creating history entries. Preserve unrecognized fields in the original artifact; normalize only supported fields. Unsupported schema versions produce an actionable error without partial import.

## Future GPS extension

Reserve optional `location` on each observation. Absence means location was not collected; it must not become coordinates (0, 0). Version 1 importers accept and preserve this object without requiring GPS permissions or providing maps.

A location object carries `status` (`available`, `unavailable`, `permission_denied`, `disabled`), `source` (`phone`, `external_receiver`, `imported`), `provider` text and `fix_utc`. Available fixes require finite WGS84 `latitude_deg` (-90 through 90), `longitude_deg` (-180 through 180), and nonnegative `horizontal_accuracy_m`. Optional fields are `altitude_m`, `vertical_accuracy_m`, `speed_mps`, `bearing_deg`, `fix_age_ms`, and `mock` (boolean). Altitude includes `altitude_reference` (`ellipsoid`, `mean_sea_level`, `unknown`); never assume altitude datum. Nonnegative accuracy, speed and age; bearing in [0, 360). Unknown values remain null. Unavailable statuses cannot carry coordinate values.

Cellular and location observation times stay separate. Later capture code must report actual fix age rather than claiming a fix was simultaneous with the radio observation. External USB GPS or gpsd observations retain their own source and timestamps. Maps, interpolation, geocoding and automatic location-based point matching are deferred. Future exports must make coordinate inclusion visible to the operator. Device location permissions required to access cell information do not by themselves authorize the companion to record coordinates.

## Desktop integration

Add a dedicated Android import/review action rather than treating the envelope as a flat metric dictionary. Show device, subscription, capture outcome, timestamps/ages and serving/neighbor tables before analysis. The operator chooses a snapshot and, if ambiguous, the serving cell. Never silently merge separate subscriptions, observations or radio legs.

Normalize only the explicitly selected, valid serving-cell measurements into existing engine fields. Preserve LTE/NR quantities in their appropriate namespaces; retain NR SS/CSI distinctions in provenance. Do not manufacture generic SINR from an unrelated quantity. Unknown registration must not become false. Neighbor observations remain reference evidence rather than feeding serving-cell diagnosis.

Preserve the exact imported bytes and SHA-256 in the generated evidence pack alongside the selected observation/cell references, field mapping and app/device provenance. Store source kind as Android import, never desktop live acquisition. The phone model identifies a source, not a calibrated RF instrument. Do not combine Android observations with desktop host metrics as though collected simultaneously.

Survey attachment requires an explicit selected point and imported snapshot. It must not overwrite an existing run or impersonate an automatic survey step. Record the original capture ID and selection, and treat Android-vs-AT receiver comparisons or unknown device/settings matches as noncomparable for numeric change until a separate compatibility rule is implemented. Imported report/history opening continues through the existing shared engine and evidence viewer.

## Validation and acceptance

- Contract fixtures: valid LTE, NR, mixed serving/neighbor, dual-SIM, cached timestamp, missing/sentinel values, denied permissions, partial/cancelled sessions and malformed input.
- Verify exact source-byte retention and evidence manifest integrity; imports never start hardware/network collection.
- Verify deterministic cell selection, no strongest-neighbor substitution, no cross-SIM mixing and no missing-to-zero conversion.
- Native Desktop review/import/reopen and survey attachment workflow checks.
- Android unit tests for serialization, API guards, unavailable-value handling and timestamp ages; build APK and inspect foreground permission/export behavior on emulator where available.
- Physical Note Ultra qualification records exact model, OS, LTE/5G availability, permissions, subscription behavior and observed fields. Unsupported and untested combinations remain labeled.

## Official API references

- https://developer.android.com/reference/android/telephony/TelephonyManager
- https://developer.android.com/reference/android/telephony/CellInfo
- https://developer.android.com/reference/android/telephony/CellSignalStrengthLte
- https://developer.android.com/reference/android/telephony/CellSignalStrengthNr
- https://developer.android.com/reference/android/telephony/CellIdentityNr

Public API updates may be rate-limited and fields may be unreported. These sources establish API capabilities, not compatibility of a specific phone/carrier combination.
