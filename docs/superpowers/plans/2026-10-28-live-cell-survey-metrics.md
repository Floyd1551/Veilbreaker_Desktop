# Live Android survey metrics implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a defensible measured-point scalar for a live Android session with one reported serving-cell group, while preserving cell/time provenance and rejecting ambiguous sessions.

**Architecture:** A pure reducer reads the already saved cellular report. It selects one group only, ignores cached or stale samples, computes a per-signal median over fresh samples and emits a separate `live_phone_*` metric namespace with count, receipt window and reported identity. The map adapter adds these values read-only; geographic and floor views consume the same derived model without changing the diagnostic or survey files.

**Tech Stack:** Python, PySide6, unittest.

**Spec:** `docs/superpowers/specs/2026-10-25-tools-and-survey-spatial-design.md`, measured-point phase C.

## Constraints

- Do not combine cells, subscriptions or radio types into one signal.
- A reported cell identity is not a physical tower or DAS antenna identity.
- Exclude cached, unknown-age and >10-second-old modem samples from the median.
- Use receipt timestamps as the aggregation window; do not imply exact over-the-air sample time.
- No per-fix measurement or interpolated surface is created.
- Older saved runs and location-only captures remain usable.

## Task 1 — Pure live-cell reducer

- [x] Add failing tests for one stable group, stale/cached exclusion, multiple groups and missing signals.
- [x] Implement a focused reducer with per-metric provenance.
- [x] Run reducer tests.

## Task 2 — Survey model and views

- [x] Add failing tests for read-only map derivation and honest ambiguous-session warning.
- [x] Feed the derived values into the geographic and floor-plan models.
- [x] Display median, sample count, receipt window and reported cell identity in point detail.
- [x] Run map and spatial UI tests.

## Task 3 — Verification and release

- [x] Update the progress guide and release notes with limitations.
- [x] Run focused/full verification and create an installer.
- [ ] Commit and push source changes.
