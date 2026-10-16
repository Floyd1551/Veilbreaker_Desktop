# Phone location and companion refresh — October 16, 2026

Implemented in desktop 0.34.0rc1 / companion 0.4.0-dev:

- Dark teal companion layout with input, connection, and capture cards.
- Readable serving-cell measurements and optional technical JSON detail.
- Explicit opt-in foreground phone GPS, including location-only acquisition without a SIM.
- USB pairing negotiates the phone's selected inputs; older companions default to cellular only.
- Location evidence tab, saved HTML tables, and CSV evidence export.
- Quality checks retain missing, stale, low-accuracy, and mock observations without treating them as qualified survey positions.
- GPS/modem timing offsets use sample ages from the same phone clock.
- Android connection/session isolation foundations and bounded authorization lifetime.

Still pending from the broader approved plan:

- Desktop survey equipment configuration and reusable approval across survey points.
- Representative positions and location export across the entire survey.
- Physical-device visual and GPS field validation.
- External USB GNSS receiver integration and maps.

Review caught and corrected a too-short standalone GPS acquisition window; it now waits up to 30 seconds for an initial fix. No location fix is fabricated when acquisition times out.
