# Manual survey placement â€” phase B

Approved design: `docs/superpowers/specs/2026-10-25-tools-and-survey-spatial-design.md`. Execute inline with test-driven development.

Build `survey_spatial.py` for versioned sidecar records, immutable PNG floor assets, per-run manual placements, scale calibration, audit history and portable export. Use survey locks, refuse edits to running/completed/trashed surveys and never modify run evidence. Validate every persisted coordinate and asset reference.

Build `survey_spatial_ui.py`: select survey step and geographic/floor view; enter coordinates or pick map location; click floor image with normalized coordinates; save/reposition/clear explicitly; import labeled floors and calibrate from two points. Floor clicks map through the displayed image rectangle. Reuse existing offline map with an opt-in coordinate-pick callback. Normal map clicks keep their previous behavior.

Integrate a placement button into survey detail; show manual geographic pins distinctly in survey maps and include spatial JSON/floor assets in survey ZIPs. Existing trash/restore retains sidecars in place and edit restrictions follow survey state. Heat maps remain phase C/D.

Verification: numeric bounds, multiple floors, scale/resize transformations, original-evidence immutability, completed/trash protection, asset integrity and export; UI click/save/clear and seven-page smoke. Run full suite and independent review before commit.

## Verification — October 26

Implemented and verified: 303 full-suite tests passed; final UI regression checks passed (2 tests); seven-page/11-calculator GUI smoke passed; offline map smoke passed. Floor editor visually inspected at 900×640. Independent review identified a GPS representative-ID mismatch and missing placement timestamp validation; both corrected. Full-suite verification also found and resolved nested survey locking during automatic export. Full Windows scaling matrix and physical field acceptance remain pending.
