# Survey Landing and Lifecycle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make surveys navigable and manageable from a dedicated landing page.

**Architecture:** Extend existing journals additively with operator lifecycle and edit history. Retain survey.py locking/atomic writes and extract detail UI from the crowded SurveyPage; reuse library tombstones for recoverable deletion.

**Tech Stack:** Python, PySide6, SQLite, JSON journals, unittest.

**Spec:** docs/superpowers/specs/2026-10-15-field-workflows-design.md

## Global constraints
- Preserve existing saved runs and journals; add fields rather than rewriting historical evidence.
- Keep phone RF separate from desktop connectivity; retain raw capture and source provenance.
- No GPS, transmission, raw baseband, cloud sync, permanent purge, or arbitrary document editing.
- Disable workspace reset and mutations affecting active work during acquisition.
- Use Python unittest and existing PySide6/SQLite/atomic JSON patterns; no new dependencies.
- Work on a codex/ branch. Commit each passing task. Native implementation is recommended; final independent review and frozen Windows checks precede pushing finished code.

## Review focus
- Legacy journals: preserve collection status while deriving lifecycle (task 1).
- Complete partially run survey: unrun is not successful (task 1).
- Add after completion or at 20 tests: enforce reopen/cap (task 1).
- Deleting survey containing shared/case-linked runs: preserve dependencies (task 3).
- Running survey edited from stale view: backend rejects mutation (tasks 1 and 3).

### Task 1: Survey lifecycle and future-test configuration

**Files:** Modify src/veilbreaker/survey.py; create tests/test_survey_lifecycle.py; extend tests/test_survey.py.

**Interfaces:** create_survey(config, name: str, steps: list[dict]) -> dict saves without running. update_survey(config, path, changes: dict) -> dict; append_steps(config, path, steps: list[dict]) -> dict; set_lifecycle(config, path, completed: bool) -> dict. read_session adds derived lifecycle for legacy data.

- [ ] Add regression tests: assert create starts no collector; legacy complete maps completed, others open; completion records pending tests not_run without altering acquired outcomes; reopen preserves IDs/evidence; 20 allowed and 21 rejected; completed survey rejects append; active lock rejects mutations; config changes affect only future steps; site change after acquisition rejected.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_survey*.py"`; confirm the new assertions fail for the intended missing behavior before implementation.
- [ ] Implement: Use existing session_lock and atomic_json. Record lifecycle events and per-step settings snapshots, with fallback to original settings for old steps. Keep failed/partial/interrupted outcomes independent of operator completion and preserve manual progression.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_survey*.py"`; require zero failures. Review the changed behavior against the spec.
- [ ] Commit this task's named files and tests; record verification in the execution ledger.

### Task 2: Landing and survey detail UI

**Files:** Modify src/veilbreaker/survey_ui.py and gui.py; create src/veilbreaker/survey_detail_ui.py and tests/test_survey_workflow_ui.py.

**Interfaces:** SurveyPage.show_landing() -> None; SurveyPage.show_session(session: dict, path: str) -> None remains compatible with worker callbacks. Detail consumes lifecycle services from task 1; New survey uses create_survey then opens detail.

- [ ] Add regression tests: assert initial page lists surveys with Open/Completed filters; selecting opens attributes/tests/reports; Back restores list; New saves without running; add/configure/complete/reopen refresh states and capacity; complete with pending tests requires confirmation; small window remains usable.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_survey*ui.py"`; confirm the new assertions fail for the intended missing behavior before implementation.
- [ ] Implement: Move builder to New/configuration flow. Detail groups attributes, tests, reports and actions; retain existing compare/trends/export and in-app reports. Keep Run next distinct from add/configure; prevent edits to completed measurements.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_survey*ui.py"`; require zero failures. Review the changed behavior against the spec.
- [ ] Commit this task's named files and tests; record verification in the execution ledger.

### Task 3: Recoverable survey removal and restore

**Files:** Extend src/veilbreaker/library.py, library_ui.py, survey.py and survey_detail_ui.py; extend tests/test_library.py and test_survey_lifecycle.py.

**Interfaces:** trash_survey(config, path, include_owned_runs: bool=False) -> str; restore_entry supports survey manifests and associated owned-run tombstones. Active list_sessions excludes trashed survey IDs; restore reuses original IDs.

- [ ] Add regression tests: assert default removal keeps tests visible as standalone; optional owned-run removal preserves shared/case references; confirmation counts match affected records; restore returns original links and refuses conflicts; interrupted transaction is all-or-nothing; running survey deletion fails; external captures/exports untouched.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_library*.py"`; confirm the new assertions fail for the intended missing behavior before implementation.
- [ ] Implement: Use SQLite removal records referencing retained survey journal/configuration rather than moving originals. Survey dependency scans must include removal metadata when needed for restore while active views exclude trashed owners. Restore linked tombstones only if still owned by that removal; independently restored runs stay intact. Also run test_survey_lifecycle.py.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_library*.py"`; require zero failures. Review the changed behavior against the spec.
- [ ] Commit this task's named files and tests; record verification in the execution ledger.

## Increment exit
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests`; require zero failures.
- [ ] Review compatibility and error paths, update user-facing documentation, and record limitations.
- [ ] Run `.venv/Scripts/python.exe tools/build_release.py` and `./build-installer.ps1 -SkipBuild` for a shipped Windows increment; require successful exit and verified manifest.
- [ ] Inspect the UI at a small usable window size, including empty, populated, and error states.
- [ ] Complete independent review, fix findings, and push verified source to GitHub. Do not claim physical-device qualification from synthetic fixtures.
