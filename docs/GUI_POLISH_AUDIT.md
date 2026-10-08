# Desktop polish audit — October 7, 2026

Scope: current native Qt UI, synthetic saved metrics and a synthetic SDR trace. Screenshots captured at 1280×800 and 1024×700 in `test-artifacts/ui-polish-before/`. No hardware acquisition or production data was used.

1. **Overview:** clear entry point and consistent dark/teal palette. Keep this visual direction and existing navigation.
2. **Diagnostics:** setup instructions, collector choices and disabled actions dominate the viewport. At 1024×700, the summary begins at the bottom edge. Make setup collapsible and show concise scenario guidance with on-demand detail. Separate results from configuration.
3. **Spectrum:** three control rows compete with the chart. Consolidate related controls, preserve chart height and keep zoom/reset/expand discoverable. Verify the entire chart fits after tab transitions and resizing.
4. **SDR report:** long caveats and raw JSON precede measurements; the report renders with a monospaced appearance. Put human-readable run context and measurement summaries first, use explicit proportional font styling, and move acquisition metadata to an optional technical section. Preserve limitations and provenance in exports.
5. **Site surveys:** builder, saved sessions and results lack clear section boundaries; queue editing and acquisition actions share one row. Group them, shorten instructional copy without changing behavior, and add a useful empty-queue message.
6. **Compact layout:** long setup guidance substantially reduces evidence visibility. Preserve keyboard navigation and readable labels as controls collapse or reflow.

Accessibility limits: screenshots establish layout/legibility issues, not screen-reader support or full contrast compliance. Existing native controls and keyboard shortcuts should be retained; focus order and narrow layouts need inspection after changes.

Proposed bounded implementation: retain palette/navigation/data flows; polish existing Diagnostics, Spectrum, SDR report, and survey builder. No new acquisition capabilities or external design service is needed.


## Implemented outcome

Approved scope implemented in 0.22.0rc1. After screenshots are under `test-artifacts/ui-polish-after/`. Diagnostics setup collapses on results; scenario detail and SDR technical metadata are available on demand; spectrum controls reflow together; survey planning has a dedicated card and useful empty state. Exports retain full report detail.

Focused native UI checks passed for scenario guidance, setup/tab transitions, technical details, report-to-spectrum navigation, adding a survey point, and absence of page-level horizontal overflow at 760px. No hardware acquisition, full regression suite, or installer lifecycle test was run. Screenshots were inspected at 1280×800 and 1024×700; these checks do not establish full accessibility compliance.
