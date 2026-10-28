# Floor-plan measured points implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show saved run metrics on placed indoor scans with floor-specific colors and clear manual-placement provenance.

**Architecture:** Reuse `survey_metrics.py` for finite values and relative colors. `SpatialDialog` derives a per-floor metric model from the already loaded survey steps and spatial sidecar, then passes marker presentation data to `FloorCanvas`. The canvas continues to emit normalized placement clicks; the selector and detail text remain native Qt controls.

**Tech Stack:** PySide6, Python, unittest.

**Spec:** `docs/superpowers/specs/2026-10-25-tools-and-survey-spatial-design.md`, measured-point phase C.

## Constraints

- Only metrics from scans placed on the selected floor contribute to its color range.
- Saved run metrics are diagnostic aggregates, not exact per-position samples or heat-map estimates.
- Manual floor position remains operator placement; no GPS evidence is created or changed.
- Missing, boolean and nonfinite metrics have no color; selection and placement remain functional without metrics.
- Existing zoom/pan and calibration behavior must keep working.

## Task 1 — Floor metric model and canvas

- [x] Write and run failing tests for floor isolation, missing values and marker colors.
- [x] Derive per-floor metric scale and render marker fill/labels with purple manual outlines.
- [x] Run floor-plan unit tests.

## Task 2 — Native floor controls

- [x] Write and run failing tests for metric selector, legend and selected-scan detail.
- [x] Add the native controls with explicit run-level provenance and missing states.
- [x] Run spatial UI and narrow-window checks.

## Task 3 — Release

- [x] Update progress guide with exact completed scope and remaining source/identity filters.
- [x] Run relevant tests, source smoke and diff checks.
- [x] Commit and push source changes.
