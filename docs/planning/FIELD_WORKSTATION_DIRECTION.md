# Field workstation direction — 2026-10-26

The user-supplied Veilbreaker UI component concept is the visual target for incremental
PySide6 development. Preserve diagnostics, evidence, survey, CLI, configuration, and reports.
Evidence clarity takes precedence over visual effects: distinguish measured, operator-entered,
reference, calculated, inferred, and estimated information in both UI and storage.

## Navigation and appearance

Target: Overview, Investigate, Evidence, Surveys, Configuration, Tools, Settings.
Investigate collects/analyzes; Evidence owns history, reports, comparison, bundles and recovery.
Configuration owns hardware, collectors, targets and readiness. Settings owns application
storage, appearance, logging, updates and advanced behavior. Avoid duplicate configuration pages.
Retain the sidebar and use dark navy/charcoal, cyan accents, restrained borders and compact
readable information. Build reusable headers, buttons, badges, cards, tables, empty states,
details, legends and metric selectors. Avoid wholesale rewrites and hardcoded page-index drift.

## Ordered delivery

1. Finish approved spatial placement: geographic and floor positions, independent floors,
   calibration, persistence, portable assets, export, trash/restore and regression coverage.
2. Tool framework: searchable registry, categories, cards, calculator host, shared result and
   schematic panels; separate computation, references, visualization and UI.
3. High-value tools: RF link budget, FSPL, EIRP/ERP, dBm conversion, wavelength, coax loss,
   Wi-Fi channel visualization, EARFCN/NR-ARFCN, cellular interpretation, MTU/MSS, BDP,
   fiber budget and PoE. Retain existing Fresnel, curvature and subnet tools.
4. Offline searchable references with category/tags/tables/diagrams, sources, version/date
   and limitations. Start with RF units/propagation, US bands, cellular metrics, Wi-Fi channels,
   networking addressing, and physical media/power. Standards content must identify its age.
5. Measured-point visualization: metric selector, legend, values, filters and details retaining
   timestamp, collector, technology, source/carrier, band/channel, provenance and run identity.
6. Guarded interpolation, explicitly **Estimated surface**, separate from **Measured points**.
   Require sample count/density/distance limits and compatible metric, source, technology,
   band/channel and floor. Never invent AP, cell, antenna or DAS transmitter identity.
7. Tool integration: save/copy/export calculations, presets, attach to investigation/survey/report,
   related references and tool chaining. Calculations never silently become measured evidence.

## Further tool batches

Categories: RF, Cellular, Wi-Fi, Networking, Fiber & Power, References.
RF expansion: aperture, loss stacks, sensitivity/noise/cascaded noise figure, SNR/fade margin,
field strength, VSWR/return loss/mismatch, polarization, log-distance, diffraction and Doppler.
Cellular: band inspection, resource blocks, numerology, TDD, timing advance, PCI and sector bearing.
Wi-Fi: PSC, PHY rate, throughput, airtime, capacity and roaming planning.
Networking: TCP estimates, serialization/latency budgets, aggregation and VLAN/VRF/subnet conflicts.
Physical: optical attenuation, connector/splice planning and portable battery/UPS runtime.
Build in small tested batches, not fifty simultaneous tools. Diagrams are labeled schematic,
never presented as measured terrain or simulated propagation without an actual model.

## Later integration

Editable equipment library with built-in versus user data provenance; Ctrl+K command palette;
local explain-this-value guidance; correlation and before/after plots; reusable field checklists.
Indoor floors eventually retain annotations and visualization state. Users can place unlocated
measurements after collection. GPS is cyan, operator placement purple, estimates a distinct layer.

## Validation

Critical tools remain offline. Cover correctness, invalid inputs, conversions, search,
persistence, export, backward compatibility and survey storage integrity. Check 1280×720,
1366×768 and 1920×1080, including Windows 100%/125% scaling. Normal pages must not require
horizontal scrolling. Hardware validation and actual field accuracy remain separate from
synthetic UI and calculation tests.
