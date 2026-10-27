# Regional Packs Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans. Each feature step begins with a failing test and ends with focused verification.

**Goal:** Manage regional terrain and physical-structure reference packs in app storage, expose coverage/provenance, support explicit HTTPS download, and use installed terrain in path assessment.

**Architecture:** `regional_packs.py` owns versioned manifests, validation, atomic local installation, listing, verification and structure queries. `regional_pack_download.py` owns bounded explicit HTTPS transfer. `regional_packs_ui.py` provides one field-friendly manager in Configuration. The path dialog accepts a selected terrain pack without bypassing existing height/datum confirmation.

**Tech Stack:** Python 3.11+, PySide6, rasterio/pyproj already packaged, unittest.

**Spec:** `docs/superpowers/specs/2026-10-27-regional-packs-design.md`.

## Review Focus

- Malformed or cancelled import/download cannot replace a valid pack.
- Source URL credentials/query parameters cannot enter a manifest or report.
- Geographic bounds and data provenance remain separate from an assertion of complete coverage.
- Structure records never become serving-cell matches.
- A missing or changed pack is visibly unavailable before assessment.

### Task 1: Local pack store

- [ ] Write tests for terrain/structure install, metadata, bounds, duplicate IDs, hash verification, cancellation and removal.
- [ ] Implement versioned store and validation in `regional_packs.py`.
- [ ] Run focused backend tests.

### Task 2: Bounded download

- [ ] Write tests for HTTPS-only URLs, streamed size/hash limits, cancellation and URL sanitization.
- [ ] Implement `regional_pack_download.py`; install only after complete verified transfer.
- [ ] Run focused transfer tests.

### Task 3: Desktop integration

- [ ] Write failing UI tests for list/import/download state and terrain assessment selection.
- [ ] Add manager to Configuration and installed-terrain selection in path assessment.
- [ ] Run focused GUI tests at field window width.

### Task 4: Release

- [ ] Document usage/source limits, run full suite and frozen smoke, build installer, verify checksum.
- [ ] Commit and push source.
