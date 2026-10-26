# Searchable Tools Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one searchable, categorized discovery surface for all existing offline calculators, the subnet inspector, and reference articles.

**Architecture:** A pure Python registry owns discovery metadata and filtering. Reusable PySide6 cards render matching records and route activation into the existing calculator, networking, and reference hosts without moving their calculation logic.

**Tech Stack:** Python 3.13, PySide6, unittest

**Spec:** `docs/superpowers/specs/2026-10-26-searchable-tools-framework-design.md`

## Global Constraints

- Preserve all current Tools behavior and offline operation.
- Discovery metadata never becomes evidence.
- Categories are RF, Cellular, Wi-Fi, Networking, Fiber & Power, and References.
- Search is case-insensitive and every non-empty query token must match the record's discovery text.
- Normal use at 1280×720 must not require horizontal page scrolling.

## Review Focus

- Duplicate IDs must fail loudly instead of routing to the wrong tool.
- Empty/repeated whitespace must behave like an unfiltered search.
- Unknown categories must return no records without throwing.
- A no-match query must expose an empty state without breaking host panels.
- Activating every record kind must select the correct existing host and item.

---

### Task 1: Registry and search contract

**Files:**
- Create: `src/veilbreaker/tool_registry.py`
- Create: `tests/test_tool_registry.py`

**Interfaces:**
- Produces: `ToolRecord`, `CATEGORIES`, `build_registry()`, and `search_registry(records, query='', category='All')`.

- [x] Write tests for unique IDs, expected current record kinds, multi-token search, category filtering, empty whitespace, and unknown categories.
- [x] Run `python -m unittest tests.test_tool_registry -v`; expect import failure.
- [x] Implement immutable records assembled from `rf_tools.TOOLS`, the subnet inspector, and `toolbox_reference.REFERENCES`.
- [x] Run the registry tests; expect pass.

### Task 2: Reusable cards and routing

**Files:**
- Create: `src/veilbreaker/tool_cards.py`
- Modify: `src/veilbreaker/toolbox_ui.py`
- Modify: `tests/test_visual_toolbox.py`

**Interfaces:**
- Consumes: registry records and stable `record_id`, `kind`, `target_id` fields.
- Produces: `ToolCard.activated(str)` and `ToolboxPage.activate_record(record_id)`.

- [x] Write UI tests proving global search/category/no-match behavior and activation routing for calculator, inspector, and reference records.
- [x] Run the visual toolbox tests; expect missing global discovery controls.
- [x] Implement cards, responsive results, empty state, and routing into existing tabs.
- [x] Run visual toolbox and registry tests; expect pass.

### Task 3: Accessibility, responsive rendering, and project verification

**Files:**
- Modify: `tests/test_visual_toolbox.py`
- Modify: `docs/planning/FIELD_WORKSTATION_DIRECTION.md`

**Interfaces:**
- Consumes: completed registry and Tools page.
- Produces: keyboard-accessible discovery and documented phase status.

- [x] Add narrow-window and keyboard activation assertions.
- [x] Run focused tests, then the full unittest suite and GUI smoke.
- [x] Render and inspect the Tools page at 1280×720 and 900×640; correct clipping or horizontal scrolling.
- [x] Record verified behavior and remaining tool batches in the field-workstation direction.

Verification: 311 tests passed, seven-page/11-calculator GUI smoke passed, and discovery renders at 1280×720 and 900×640 showed wrapped cards with no horizontal scrolling. Independent review found card-focus and internal-kind search defects; both were reproduced with failing tests and corrected before the final suite.

**Ruling:** `docs/ROADMAP.md` contains a legacy non-UTF-8 byte and could not be safely patched with the repository editing workflow. Record this phase in the field-workstation direction instead; the product direction remains the roadmap authority for this work.
