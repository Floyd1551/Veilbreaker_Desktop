# Survey Measured Map Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Color geographic survey points by a selected saved diagnostic metric while preserving location provenance and metric provenance.

**Architecture:** A small pure module selects finite, supported run metrics and calculates a relative measured-value color scale. The map adapter carries per-run saved metrics without changing evidence. The native map dialog presents a selector, legend and value detail; MapLibre renders the selected color while retaining manual/GPS outlines.

**Tech Stack:** Python, PySide6, bundled MapLibre JS, unittest.

**Spec:** `docs/superpowers/specs/2026-10-25-tools-and-survey-spatial-design.md`, heat-map stage C, initial geographic slice.

## Global Constraints

- A run metric is a saved diagnostic aggregate, not a value measured at each GPS fix or a transmitter-specific signal.
- Missing, nonfinite, boolean and unsupported values are not colored.
- Colors show relative observed values and must not imply universal quality thresholds.
- Manual placement remains operator-supplied; GPS remains captured evidence.
- No network dependency, interpolation, evidence mutation or invented AP/cell identity.

## Task 1 — Run metric model

- [x] Add failing tests for saved run metrics, missing/invalid values and finite selection.
- [x] Add a focused `survey_metrics.py` module and map-source adapter changes.
- [x] Run map-source and metric tests.

## Task 2 — Geographic map presentation

- [x] Add failing UI tests for selector, legend, details and provenance.
- [x] Add selector and legend to `map_ui.py`; pass selected point colors to MapLibre.
- [x] Update `assets/maps/app.js` to render measured fills with provenance outlines.
- [x] Run map UI, map data and narrow-screen checks.

## Task 3 — Verification and release

- [x] Update progress checklist with exact scope.
- [x] Run focused tests, source smoke and diff checks.
- [x] Build and verify the 0.55 Windows installer.
- [x] Commit and push source changes to the authorized repository.
