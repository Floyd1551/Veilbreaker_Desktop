# Diagnostic Evidence and Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make phone/SDR evidence actionable and let operators clear Diagnostics.

**Architecture:** Introduce a structured receiver-assessment adapter while preserving existing metrics and report serialization. Integrate findings into all existing report surfaces; keep GUI reset as a single method.

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
- Later samples omit an earlier metric: retain its timestamp and mark it historical (task 1).
- One phone exposes multiple LTE/NR cells: no strongest-cell substitution (task 1).
- Old SDR records lack settings: no qualified anomaly comparison (task 2).
- Cleared report still has hidden plot/input state: reset all result surfaces (task 3).
- Reset invoked while worker runs: refuse without changing acquisition (task 3).

### Task 1: Structured phone assessment

**Files:** Create src/veilbreaker/receiver_assessment.py and tests/test_receiver_assessment.py; modify android_import.py, core.py, cellular_report.py and tests/test_android_import.py under their existing directories.

**Interfaces:** build_phone_assessments(envelope: dict) -> list[dict] returns stable receiver_id, source, radio, identity, measurements (value/unit/received_utc/age_ms/current), findings and availability. Store under report.normalized_metrics["receiver_assessments"]. apply_phone_assessments(report, assessments) -> None adds source-labelled findings/summary without overwriting desktop RF metrics.

- [ ] Add regression tests: assert live weak-RSRP evidence appears in main findings; healthy readings do not generate missing-phone-RSRP; absent values remain unknown; LTE and NR metrics stay separate; multiple cells stay separate; last missing sample marks retained measurement current=False; repeated samples retain age; saved selection assesses only its selected cell; report JSON contains no token; desktop rsrp=-80 remains -80.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*android*.py"`; confirm the new assertions fail for the intended missing behavior before implementation.
- [ ] Implement: Use stable cell keys shared with cellular reporting. Preserve selected saved-input scope and all registered live cells. Call the existing RF rules per receiver with timestamps and source labels; do not average health scores across receivers. Scope missing-data findings and availability by receiver, and expose the structured assessment in main HTML and in-app findings. Also run test_receiver_assessment.py and test_cellular_report.py.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_*android*.py"`; require zero failures. Review the changed behavior against the spec.
- [ ] Commit this task's named files and tests; record verification in the execution ledger.

### Task 2: Qualified SDR interpretation

**Files:** Modify src/veilbreaker/core.py and sdr_report.py; create src/veilbreaker/sdr_assessment.py and tests/test_sdr_assessment.py.

**Interfaces:** compare_capture_context(current: dict, baseline: dict) -> dict with compatible: bool and reasons: list[str]. assess_sdr(summaries: list[dict], context: dict, baseline: dict | None) -> dict with observations, findings, next_tests and comparison qualification.

- [ ] Add regression tests: assert concentration explains relative excess and next measurement; compatible baseline rises produce evidence; changed gain/bin width/coverage/receiver or missing context suppress qualified baseline anomaly; band-plan match never asserts carrier identity; temporal claim requires multiple sweeps; empty sweeps yield unavailable rather than healthy.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_sdr*.py"`; confirm the new assertions fail for the intended missing behavior before implementation.
- [ ] Implement: Trace existing sweep metadata and baseline storage, add context metadata for new records, and reject comparisons whose required context is absent. Replace duplicate SDR rule execution with shared structured assessment used by main and dedicated reports. Preserve existing relative-power units and plots.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_sdr*.py"`; require zero failures. Review the changed behavior against the spec.
- [ ] Commit this task's named files and tests; record verification in the execution ledger.

### Task 3: Clear workspace

**Files:** Modify src/veilbreaker/gui.py; extend tests/test_gui.py.

**Interfaces:** MainWindow.clear_workspace() -> None is the sole idle reset entry point; existing busy handling enables/disables its button.

- [ ] Add regression tests: load a run then clear: assert payload is empty, all result tables and plot selectors are empty, report viewers show empty states, input and Android credentials/retry references are cleared, result-dependent actions disabled, settings and stored run count unchanged; reload works; busy clear is refused.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_gui.py"`; confirm the new assertions fail for the intended missing behavior before implementation.
- [ ] Implement: Add Clear workspace beside diagnostic actions. Reset every field populated by display_payload, follow-up selection, input attachment and progress without deleting files or resetting collector/site/scenario configuration. Include spectrum comparison state and filter counts.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_gui.py"`; require zero failures. Review the changed behavior against the spec.
- [ ] Commit this task's named files and tests; record verification in the execution ledger.

## Increment exit
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests`; require zero failures.
- [ ] Review compatibility and error paths, update user-facing documentation, and record limitations.
- [ ] Run `.venv/Scripts/python.exe tools/build_release.py` and `./build-installer.ps1 -SkipBuild` for a shipped Windows increment; require successful exit and verified manifest.
- [ ] Inspect the UI at a small usable window size, including empty, populated, and error states.
- [ ] Complete independent review, fix findings, and push verified source to GitHub. Do not claim physical-device qualification from synthetic fixtures.
