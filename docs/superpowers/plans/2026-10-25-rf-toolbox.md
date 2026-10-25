# RF toolbox implementation plan

> Execute inline using superpowers:executing-plans.

**Goal:** Deliver the first offline calculators from the accepted field-platform roadmap, as requested by the user on October 25.

**Architecture:** A pure Python calculator registry and validation layer serves a reusable PySide6 dialog opened from Tools & readiness. Results contain named inputs/outputs, units, method and limitations. Calculation snapshots are copyable; persisted survey attachments are a subsequent increment.

**Tech stack:** Existing Python / PySide6; no new dependencies.

**Scope:** Power conversion (dBm, mW, W), wavelength, free-space path loss, EIRP and link budget with receiver sensitivity/fade margin. Searchable selector, readable results and inline errors. Use exact vacuum light speed for wavelength/FSPL, explicit MHz/km inputs and dBi gains. No terrain/LOS inference or regulatory compliance verdict.

- [x] Write failing independent numeric/invalid-input tests in `tests/test_rf_tools.py`.
- [x] Implement immutable tool definitions and `calculate(tool_id, inputs)` in `src/veilbreaker/rf_tools.py`.
- [x] Write UI tests for selection, invalid input and stale-result prevention.
- [x] Implement `src/veilbreaker/rf_tools_ui.py`; add launcher to `gui.py` without changing capture/readiness controls.
- [x] Run targeted tests and desktop integration checks; document tools and limitations.

Verification: 272 source tests passed before the review fix; all 6 targeted RF tests passed after it. Six-page desktop smoke passed. Reviewed the rendered dialog with Windows fonts. Independent review found search resetting unchanged-tool inputs; fixed and regression tested. No installer built for this increment.
