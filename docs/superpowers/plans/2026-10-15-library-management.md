# Test Library Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Provide recoverable test/report deletion and restoration.

**Architecture:** Add a focused library service and SQLite tombstones. Keep run artifacts in place while hidden by tombstones, so removal is atomic and restore needs no file moves; survey journals use a recoverable removal record in phase 3.

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
- Case/survey-linked run deletion: block and explain owner (task 1).
- Malicious artifact path: no external filesystem mutation (task 1).
- Restart during removal: one atomic transaction preserves evidence (task 1).
- Trashed runs leaking into baselines or comparisons: filter every active query (task 1).
- Restore ID conflict: refuse overwrite (task 2).

### Task 1: Library service and active-query filtering

**Files:** Create src/veilbreaker/library.py and tests/test_library.py; modify VeilbreakerStore in src/veilbreaker/core.py.

**Interfaces:** run_dependencies(config, run_id: str) -> dict; trash_run(config, run_id: str) -> str returns removal ID; list_trash(config) -> list[dict]; restore_entry(config, entry_id: str) -> None. Add additive trash_entries table storing item kind/id, time and original metadata; unique active removal per item.

- [ ] Add regression tests: assert unreferenced removal leaves artifacts/raw inputs untouched, hides run from search/list/preceding/baselines, is retry-safe, survives reopen; linked case/survey blocks deletion; rollback leaves run active; malformed/outside paths never cause file mutation.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_library.py"`; confirm the new assertions fail for the intended missing behavior before implementation.
- [ ] Implement: Use transactional tombstones and preserve original rows/artifacts. Route active-run queries through a consistent not-trashed predicate, including survey comparisons and baseline queries. Resolve dependencies from journals and cases before mutation. No permanent purge. Keep direct recovery lookups explicit.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_library.py"`; require zero failures. Review the changed behavior against the spec.
- [ ] Commit this task's named files and tests; record verification in the execution ledger.

### Task 2: Library and Trash UI

**Files:** Modify src/veilbreaker/gui.py; create src/veilbreaker/library_ui.py and tests/test_library_ui.py; extend tests/test_history_search.py.

**Interfaces:** Library actions consume task 1 services. TrashDialog(config, parent=None) lists removals and restores selected entries. Delete confirmation names test and dependencies; opening a blocked owner routes to its survey/case view.

- [ ] Add regression tests: assert delete cancel leaves data active; confirmed delete refreshes counts and clears displayed deleted run; Trash restore returns run and reports; conflict refuses overwrite; empty/paged/search results update correctly; active worker disables deletion.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_library*.py"`; confirm the new assertions fail for the intended missing behavior before implementation.
- [ ] Implement: Retain existing history search and pagination with concise Open/View reports/Export/Delete actions and Trash access. Add survey association plus collection/assessment state. Keep comparison available as secondary action; report missing artifact errors without losing records. Also run test_history_search.py.
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests -p "test_library*.py"`; require zero failures. Review the changed behavior against the spec.
- [ ] Commit this task's named files and tests; record verification in the execution ledger.

## Increment exit
- [ ] Run `.venv/Scripts/python.exe -m unittest discover -s tests`; require zero failures.
- [ ] Review compatibility and error paths, update user-facing documentation, and record limitations.
- [ ] Run `.venv/Scripts/python.exe tools/build_release.py` and `./build-installer.ps1 -SkipBuild` for a shipped Windows increment; require successful exit and verified manifest.
- [ ] Inspect the UI at a small usable window size, including empty, populated, and error states.
- [ ] Complete independent review, fix findings, and push verified source to GitHub. Do not claim physical-device qualification from synthetic fixtures.
