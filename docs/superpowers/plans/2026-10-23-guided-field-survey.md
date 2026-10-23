# Guided Field Survey Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement inline.

**Goal:** Guide the next survey point from saved-settings readiness through capture and review.
**Architecture:** Share effective point settings between execution and a passive worker check; add an integrated guidance panel to SurveyPage. Context fingerprints reject stale results.
**Tech Stack:** Python, PySide6, existing JSON worker protocol and unittest.
**Spec:** ../specs/2026-10-23-guided-field-survey-design.md

## Constraints and review focus

No new collection, automatic retries, pairing, evidence schema or mandatory readiness gate.
Preserve manual/batch behavior, legacy snapshot errors, per-point settings, current storage root, and completed/running protections.
Late results after changing surveys/settings must not display. Readiness errors/cancellation must not leave a checking state. Narrow windows must remain usable.

## Task 1 — Saved-settings readiness

- [x] Add tests in tests/test_survey_flow.py for per-point overrides, legacy fallback/missing snapshots, completed/running rejection and worker dispatch.
- [x] Run tests and confirm failure before implementation.
- [x] Add effective_step_config in survey.py and use it in _run_session; create survey_flow.py with next_point_context and check_next_readiness. Context includes path, next run ID, options and a SHA-256 of effective settings; do not return credentials/settings.
- [x] Dispatch survey_readiness in jobs.py; return a distinct survey_readiness result without acquisition.
- [x] Run survey and worker tests, then commit.

## Task 2 — Integrated survey guidance

- [x] Add GUI tests for readiness dispatch, stale response rejection, manual/batch labels, completed and partial review states.
- [x] Run tests and confirm failure before implementation.
- [x] Add next-point summary, prerequisite table and review action in survey_ui.py. Invalidate checks on context change; disable controls while busy; retain the existing capture button with explicit progression labels.
- [x] Route worker results in gui.py to the survey page; handle cancellation/failure through cleanup.
- [x] Run full tests and narrow-layout checks; obtain a final independent review, address actionable findings, commit and push under existing authorization.
- [x] Update release notes and roadmap. Build a new Windows release/installer and inspect CI qualification.

## Execution record

Approved design: user approved October 23. Inline execution selected to keep this focused change inexpensive. Existing push authorization applies. No physical hardware qualification is claimed.

Progress: saved-setting and panel tests passed RED/GREEN. Added real-worker delivery, narrow detail layout, failed-point review and cancellation cleanup regression tests. Review identified stale detail after cancellation; fixed and verified. Independent reviewer stopped at account limit; remaining review performed inline. No new delegation requested.

Verification: 259 source tests passed; frozen CLI, Unicode worker, six GUI pages, offline map and terrain checks passed. Local installer compiled and checksum verified; Windows and Linux CI release/installer checks passed (run 40005674345). Review was partial due to reviewer quota; its cancellation finding was reproduced RED, fixed, and verified GREEN.
