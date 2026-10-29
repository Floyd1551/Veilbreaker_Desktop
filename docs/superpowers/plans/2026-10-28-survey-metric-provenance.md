# Survey metric provenance implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make saved survey metric sources and capture timing visible and filterable without merging desktop, phone, and imported measurements.

**Architecture:** Extend the read-only map adapter with bounded collection metadata from each run's artifact directory. A focused provenance helper returns the recorded collector IDs and timestamps for each saved metric. Geographic and floor-plan metric views share source filtering and provenance labels, while each keeps its existing position and color semantics.

**Tech Stack:** Python, PySide6, unittest.

**Spec:** `docs/superpowers/specs/2026-10-25-tools-and-survey-spatial-design.md`, measured-point phase C.

## Constraints

- A collector source is shown only if persisted `metric_sources` names it; missing attribution stays unknown.
- A phone observation receipt time is distinct from the desktop collection/import time.
- Captured identity must not be guessed from PCI, carrier name, or band alone.
- Do not fabricate a scalar from a multi-cell live Android session.
- Source filtering only changes presentation, never saved survey or diagnostic evidence.
- Existing maps/floor plans without collection metadata remain usable.

## Task 1 — Provenance adapter and metric catalog

- [x] Add failing tests for SQLite-backed source/timing metadata, missing collection files and separate phone metric keys.
- [x] Extend `map_sources.py` and `survey_metrics.py` with bounded, read-only provenance.
- [x] Run data and adapter tests.

## Task 2 — Geographic source filter

- [x] Add failing native-map tests for source-specific points and timing detail.
- [x] Add a source selector and contextual detail/legend in `map_ui.py`.
- [x] Run map tests and offline renderer smoke.

## Task 3 — Floor-plan source filter

- [x] Add failing floor-plan tests for per-floor source filtering and selected-scan provenance.
- [x] Reuse the adapter metadata in `survey_spatial_ui.py` without modifying placement data.
- [x] Run spatial UI tests and narrow-window checks.

## Task 4 — Verification and release

- [x] Update progress guide with exact scope and remaining identity/live-session limits.
- [x] Run focused/full verification and package an installer.
- [x] Commit and push source changes.
