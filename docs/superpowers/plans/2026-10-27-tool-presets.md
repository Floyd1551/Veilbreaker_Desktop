# Calculator Presets Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for this approved roadmap increment. Complete each task with a red/green test cycle.

**Goal:** Save, reload, and remove named calculator input presets across app restarts without treating them as measured evidence.

**Architecture:** A small versioned JSON store under the configured Veilbreaker data root owns validation and atomic persistence. The existing calculator panel exposes presets for its selected tool. Independent Tools tabs share the store but keep their current unsaved inputs until the operator explicitly loads a preset.

**Tech Stack:** Python 3.11+, PySide6, unittest, local JSON.

**Spec:** `docs/planning/FIELD_WORKSTATION_DIRECTION.md` section 7 and the user-approved Tools roadmap.

## Global Constraints

- Presets contain operator-entered inputs and optional notes, never captured measurements.
- They work offline on Windows and Linux.
- Existing calculation snapshots and results remain unchanged.

## Review Focus

- A malformed store must be reported and never overwritten silently.
- A preset for another tool must not load into the current tool.
- Inputs loaded from a preset invalidate any existing result until recalculated.
- Duplicate names are allowed, but each preset has a stable identity.
- File writes must be atomic and preserve earlier presets when adding/removing one.

### Task 1: Versioned preset storage

**Files:** create `src/veilbreaker/tool_presets.py`; create `tests/test_tool_presets.py`.

- [ ] Write failing tests for save/reload, validation, malformed storage, duplicate names, and delete.
- [ ] Implement `list_presets`, `save_preset`, and `delete_preset` using the calculator catalog and atomic JSON replacement.
- [ ] Run `tests.test_tool_presets` and confirm green.

### Task 2: Calculator panel controls

**Files:** modify `src/veilbreaker/rf_tools_ui.py`, `src/veilbreaker/toolbox_ui.py`; extend `tests/test_rf_tools_ui.py` and `tests/test_visual_toolbox.py`.

- [ ] Write failing UI tests for saving, loading, filtering, invalidation, and independent tab state.
- [ ] Add preset selector and Save/Load/Delete controls with a small name/notes dialog.
- [ ] Run focused UI tests and confirm green.

### Task 3: Release verification

**Files:** update README and version files.

- [ ] Run full tests and source GUI smoke.
- [ ] Build installer and verify checksum and frozen smoke.
- [ ] Commit and push the source after verification.
