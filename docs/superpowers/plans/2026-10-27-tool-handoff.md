# FSPL to Link Budget Handoff Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans and verify each task with a red/green test cycle.

**Goal:** Carry a calculated free-space path loss into a fresh Link budget tab while retaining its source and assumptions in the new result.

**Architecture:** A pure handoff builder validates the source calculation and returns one destination input plus origin metadata. The calculator panel emits an explicit request only after a valid FSPL result. The Tools workspace creates a new Link budget tab, preserving any existing tab and requiring the operator to review remaining inputs and press Calculate. Result text and JSON include the source; changing the transferred path-loss value removes that source claim.

**Tech Stack:** Python 3.11+, PySide6, unittest.

**Spec:** `docs/planning/FIELD_WORKSTATION_DIRECTION.md` section 7 and the user-approved Tools roadmap.

## Global Constraints

- Source and destination are calculated estimates, never measured evidence.
- Handoff does not run a diagnostic or automatically calculate a link budget.
- An existing Link budget tab and its inputs remain unchanged.
- Free-space loss is an ideal model; its limitation must travel with the result.

## Review Focus

- Invalid or stale source snapshots cannot be handed off.
- Editing path loss removes the source claim; editing other link-budget fields retains it.
- Copy and export contain the same provenance shown on screen.
- Repeated handoffs create independent tabs and close cleanly.

### Task 1: Pure handoff mapping

**Files:** create `src/veilbreaker/tool_handoff.py` and `tests/test_tool_handoff.py`.

- [ ] Write failing tests for valid mapping, invalid source, and changed output.
- [ ] Implement `fspl_to_link_budget(snapshot)` with recalculation validation.
- [ ] Run focused tests.

### Task 2: UI and exported provenance

**Files:** modify `rf_tools_ui.py`, `rf_tools.py`, `toolbox_ui.py`; extend focused UI tests.

- [ ] Write failing tests for visible handoff action, new independent tab, source retention/invalidation, and text/JSON output.
- [ ] Implement the signal, new-tab action, and optional source section on the destination snapshot.
- [ ] Run focused tests and narrow-window check.

### Task 3: Release

- [ ] Update README/version, run full tests and frozen checks, build installer, verify checksum.
- [ ] Commit and push source.
