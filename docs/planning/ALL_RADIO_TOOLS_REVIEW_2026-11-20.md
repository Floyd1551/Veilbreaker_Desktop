# All Radio Tools reference review

The operator supplied an archive of [All Radio Tools](https://github.com/ToftMalone/All-Radio-Tools).
Its included license is GPL-3.0. This review uses the archive as a feature
reference; Veilbreaker's implementation, wording, artwork and tests are original.
Direct reuse of its code, assets or bundled data would require a separate license
and attribution review. The project's descriptions are feature claims, not
independent evidence of device compatibility or measurement accuracy.

## Useful directions for Veilbreaker Mobile

- **Cellular:** an operator-started serving-cell identity timeline, with
  timestamps and confidence limits; a reported change does not establish a
  physical tower change or the reason for it.
- **GNSS:** a satellite sky plot using Android-reported azimuth and elevation,
  with used-in-fix and unavailable/stale data distinguished. Later investigate
  position-source comparison and optional raw measurement export, conditional on
  device/API support.
- **Wi-Fi:** more detailed security/standards inventory and explicit Wi-Fi RTT
  capability and permissions. Treat access-point observations and inferred
  identities separately.
- **Bluetooth:** an opt-in BLE inventory and GATT inspection as a separate
  future capability, with Android permissions and privacy made visible.
- **USB SDR:** investigate receive-only support and real device qualification
  later; the supplied project reports some non-HackRF drivers as untested on
  physical hardware.

The archive includes France-specific tower references and regional radio
defaults. They should not be carried over as US assumptions. Veilbreaker
should use sourced, region-appropriate data and preserve the distinction between
measurement, operator input and inference.
