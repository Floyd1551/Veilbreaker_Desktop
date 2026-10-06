# SDR context implementation plan

> Execute inline with superpowers:executing-plans, using test-driven-development.

**Goal:** Explain scenarios, provide an offline U.S. spectrum reference, and export independent SDR diagnostics.

**Architecture:** Separate scenario guidance, validated band reference data, and SDR reporting from the existing Qt orchestration. Preserve raw evidence and existing scenario IDs. Spectrum overlays annotate expected uses only.

**Tech stack:** Python, PySide6, unittest, local JSON/CSV, HTML.

- [x] Add failing tests for scenario truthfulness, band import validation/boundaries, and missing/partial SDR evidence.
- [x] Implement `scenarios.py`, `bandplan.py`, bundled U.S. reference, and `sdr_report.py`; pass focused tests.
- [x] Wire scenario help, spectrum overlays/legend/import, and SDR report view/export into Qt. Include dedicated reports in new evidence packs. Test UI selection, overlay propagation, and exports.
- [x] Document import schema and reference limitations. Run full regression suite and inspect rendered UI at narrow size.
- [x] Package next release, verify frozen smoke and isolated installer lifecycle, commit and push.


## Execution notes

- Initial tests failed for absent modules/UI/export files, then passed after implementation.
- Independent review found coverage inflation from summary-derived bin spacing and an unhandled numeric overflow in imports. Both reproduced in failing tests and corrected; CSV interval union now determines coverage.
- User supplied matching 154-row CSV/JSON references mid-release. Ruling: support their column aliases, JSON arrays, and zero-width frequency markers; bundle the supplied annotations as the default with explicit provenance, retain the independently checked smaller FCC plan as an alternate.
- Ruling: preserve public GitHub push authorization from user; execute inline and package after full verification.

Verification: 115 tests passed; frozen CLI/GUI and evidence manifest checks passed; Windows installer install/reinstall/uninstall lifecycle passed under isolated identity. Screenshots inspected at 1024x700. No live RF capture was performed for this release. Native Linux verification remains with GitHub CI.
