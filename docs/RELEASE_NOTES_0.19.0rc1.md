# Veilbreaker 0.19.0rc1

October 5, 2026. This release candidate consolidates the desktop and survey improvements since the initial recovery baseline.

- Survey sessions of 1–20 tests with manual progression, settings snapshots, audited point notes, templates and independent evidence per visit.
- Repeat-visit comparison and per-point multi-visit trends with explicit gaps, compatible-only statistics and JSON/CSV export.
- Survey search/state filters, queue rename/reordering and duplicate-label prevention.
- Confirmed cases with operator verification, withdrawal, timestamped event records, source reopening, search/paging and export.
- Full-history search/paging, responsive navigation, persistent task progress, metric filtering and validated network/hardware forms.
- Durable interrupted-capture recovery, acquisition provenance, repeatable receive presets and compatible saved-spectrum comparison.
- Windows packaging isolates dependency discovery from unrelated host DLLs and verifies the frozen GUI through both console and desktop entry points.

## Validation

104 source tests passed. Frozen CLI/GUI checks and isolated Windows install/reinstall/uninstall passed. A five-visit synthetic frozen trend test retained three comparable observations and two exclusions; all original bundles were unchanged. Existing user installation was preserved.

## Limits

GPS/maps, physical reconnect/failure qualification, native Linux qualification, clean-machine Windows qualification and code signing remain pending. Numeric changes are not automatic improvement scores; matching settings do not prove identical hardware or field conditions. Case records are operator assertions. Evidence hashes establish consistency, not authorship or accuracy.

Local installer and portable archive are under `dist`; generated artifacts, captures, configuration and backups are excluded from source control. GitHub Actions builds platform artifacts on pushes; passing local Windows checks does not establish CI or native Linux success.
