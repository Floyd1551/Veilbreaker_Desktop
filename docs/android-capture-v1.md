# Android cellular capture format v1

Status: Desktop import implemented; companion APK and physical phone qualification are not yet delivered. The example is synthetic.

Use `examples/android-cellular-v1.json` as the normative minimal example. Envelope format is `veilbreaker.android.cellular`, integer schema_version 1, UUID capture_id, UTC created_utc, device metadata, collection, subscriptions and observations. Files are UTF-8 JSON, at most 16 MiB, with no duplicate JSON keys or nonfinite numbers. At most 1,000 uniquely identified observations, 32 uniquely keyed subscriptions and 256 cells per observation. Unknown fields are preserved in original bytes but do not automatically enter diagnosis.

Device fields: manufacturer, model, android_version and companion_version strings; integer api_level >=29. Collection fields: mode snapshot/session, started_utc, ended_utc, outcome complete/partial/cancelled/failed, permissions object and notes array. Observation fields: observation_id, subscription_key referencing subscriptions[].key, received_utc, nonnegative elapsed_realtime_ms, outcome and cells. UTC timestamps require an explicit zero offset or Z.

Each cell has a radio string, registered boolean or null, connection_status primary/secondary/none/unknown, age_ms (nonnegative or null), identity object and signal object. Missing registration stays unknown. Only explicitly registered LTE/NR primary or secondary cells may be selected for analysis. CellInfo types other than LTE/NR can be preserved and inspected but cannot be analyzed in this release. No strongest-cell selection or merging of subscriptions is performed.

Identity fields: pci, earfcn, nrarfcn, bandwidth_khz and tac are nonnegative integers below Android's integer unavailable sentinel; cell_id, mcc and mnc are strings (preserve leading zeros); bands is a list of positive integers. Identity fields may be absent/null. Unknown identity fields stay in the source.

Signal fields are objects with value and unit; a null value requires reason not_reported/unsupported_api/permission_denied/timeout/unknown. LTE: rsrp(dBm), rsrq(dB), rssi(dBm), rssnr(dB), cqi(index), timing_advance(index). NR: ss_rsrp(dBm), ss_rsrq(dB), ss_sinr(dB), csi_rsrp(dBm), csi_rsrq(dB), csi_sinr(dB). Android sentinel values must be converted to null by the producer. Unknown quantities are retained in the original source only. RSSNR is retained as android_rssnr rather than silently substituted for generic SINR; NR CSI measurements do not substitute for SS measurements.

The optional observation.location contract is defined in the Android design specification. Imports preserve validated coordinates, accuracy, timestamp and source metadata, but do not collect location or provide maps. Absent location is not (0,0). Phone monotonic timestamps are not compared with the Desktop clock; age_ms describes the modem sample age when the phone received it, not its age at import.

## Desktop workflow

Diagnostics → Import Android capture → choose observation → choose serving cell → Import. Review destination site/scenario before importing. Cancel creates no history. Changed source files require a new preview. Reimporting an existing capture requires the explicit repeat checkbox; each repeat creates a new run and retains the same source ID.

Evidence contains exact android-capture.json bytes plus android-selection.json with source hash, selected cell, subscription, timing, device, location and field mapping. Collection source is android_import, and source collection/observation outcomes remain visible. No live desktop measurements are mixed into the import. Historical baseline/case matching and numeric history comparisons are withheld until receiver/settings compatibility is established. Source bytes and their hash establish file consistency, not authenticity of phone measurements.

USB file transfer can carry a compatible JSON export into Desktop. The companion producer and direct live USB transport remain separate implementation phases. Existing flat metric import is unchanged.
