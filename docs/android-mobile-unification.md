# Veilbreaker Mobile consolidation

Veilbreaker Mobile is the single Android field application. Its first
consolidation phase builds on the current companion because that app implements
Desktop's established USB pairing, cellular evidence and optional location
contract. The recovered Veilbreaker Mobile v0.3.0 source is a separate earlier
project; it contains Wi-Fi, diagnostics, a local survey database and PDF/GeoJSON
reporting. Bring those capabilities forward in independently verified slices.

## Compatibility and evidence

- Preserve Android application ID `com.veilbreaker.companion`, the existing
  USB protocol and Desktop capture schema while developing the unified app.
- Keeping an ID alone does not guarantee an in-place upgrade: Android also
  requires a compatible signing identity. Current APKs are debug builds.
- The older Mobile app used `com.outpostrelay.veilbreakermobile`. Its private
  database is not automatically accessible to this app. A future migration
  needs an explicit export and import flow; do not claim data has migrated.
- Cellular values are what Android's public APIs expose, not a complete modem
  decode. Do not infer unreported identities or claim a channel-derived band
  is confirmed by the modem.
- Distinguish observed data, operator input, cached samples, calculated values
  and estimates. Location remains explicitly opted in. Wi-Fi scans and their
  timestamps can be cached or unavailable due to permissions, platform
  throttling, radio state, or manufacturer behavior.
- Desktop USB connection remains foreground-only, locally bound and explicitly
  approved. Switching away from that connection must not silently interrupt an
  active capture.

## Phased delivery

1. **One Android entry point and Wi-Fi inspection.** Retain the companion's
   working cellular/location USB transport, and add a standalone, read-only
   view of connected Wi-Fi and cached nearby observations. This view is not yet
   a Desktop collector or part of the cellular export schema.
2. **Standalone diagnostics.** Evaluate the recovered transport-bound network
   tests against the current Desktop evidence model, explicit endpoints,
   cancellation, permission and data-quality behavior before porting.
3. **Mobile surveys and migration.** Design versioned, user-controlled
   interchange for prior Mobile survey data and Desktop surveys. Preserve GPS
   quality, source and capture timestamps; never convert manual positions into
   GPS evidence. Separate measured points from interpolated surfaces.
4. **Reports and tools.** Bring over useful on-device reports and calculators
   after verifying their calculations, evidence labels and offline behavior.
   Reassess the old position score, heatmap and automatic recommendations
   before reuse; they are not validated Desktop conclusions.
5. **Field qualification and release.** Exercise permission denial, cached and
   redacted data, SIM changes, USB disconnects and lifecycle changes on supported
   devices. Establish reproducible release signing and an upgrade/migration
   procedure before distributing a production APK.

The recovered source is in the user's local Veilbreaker backup under
`Mobile/Latest_Available_Source/VeilbreakerMobile_v0.3.0`; the implementation
in this repository remains the maintained source for the unified application.
