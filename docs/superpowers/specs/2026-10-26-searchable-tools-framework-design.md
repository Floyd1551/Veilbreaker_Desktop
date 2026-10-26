# Searchable Tools Framework Design

## Intent

Turn the existing Tools page into one offline workbench where an engineer can find and open calculators, inspectors, and references from one search field. Preserve every existing calculator, diagram, subnet result, copy/export action, and reference article.

## Scope

This phase adds a pure-data tool registry, category and text filtering, reusable compact result cards, and routing from a result into the existing host panels. Categories are RF, Cellular, Wi-Fi, Networking, Fiber & Power, and References. Empty categories remain visible so later tools have stable homes. Search is case-insensitive, ignores repeated whitespace, and matches all supplied terms against title, description, category, and keywords.

The page retains the existing calculator, networking, and reference panels. Opening a result selects the appropriate panel and record. The registry contains discovery metadata only; calculation and reference bodies remain in their existing modules. No presets, saved calculations, equipment library, command palette, new formulas, or evidence attachment are included in this phase.

## Approaches

Considered rebuilding Tools as a new stacked page, adding search independently to every tab, and placing a registry-backed discovery layer above the existing hosts. The approved incremental direction favors the registry-backed layer: it preserves mature behavior, creates one extension point, and avoids a high-risk rewrite. Independent per-tab search would continue today’s fragmented discovery; a rebuild would duplicate tested calculator UI.

## UI behavior

The page begins with a global search, category selector, result count, and responsive card area. Each card identifies category and type, gives a one-line purpose, and opens the existing tool/reference. Search and category changes update results immediately. With no matches, the page shows a useful empty state and leaves existing hosts available. Keyboard activation of a focused card opens it. The design uses the existing dark theme, restrained borders, cyan accent, and wrapping layout.

## Evidence and offline boundaries

All discovery data is bundled locally and search requires no network. Calculator output remains labeled calculated estimate. References retain their existing source links and review date. Opening or searching a tool does not create evidence or modify investigations or surveys.

## Verification

Test registry uniqueness, stable categories, multi-term/keyword/category search, whitespace and empty searches, no-match behavior, card activation routing, preserved calculator state behavior, and narrow-window wrapping. Run the full suite and the seven-page GUI smoke.
