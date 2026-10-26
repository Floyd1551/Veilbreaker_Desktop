# Visual toolbox phase A

User approved the design in `docs/superpowers/specs/2026-10-25-tools-and-survey-spatial-design.md` on October 25, 2026. Execute inline using executing-plans and test-driven-development.

Goal: Tools workspace with embedded calculators, Fresnel/curvature diagrams, offline references/charts and subnet inspection. Manual placement/heat maps are approved later phases, not part of this increment.

Files: `rf_diagrams.py` supplies pure sampled geometry plus native QWidget rendering; `rf_tools_ui.py` embeds it and invalidates stale diagrams; `toolbox_ui.py` hosts calculator, subnet and reference tabs; `toolbox_reference.py` holds original source-linked articles; `network_tools.py` wraps Python ipaddress for bounded local IPv4/IPv6 arithmetic. Existing GUI indexes remain stable by appending Tools.

- Test geometry invariants, invalidation, subnet boundaries, reference search and responsive navigation.
- Implement diagram geometry using the existing terrain engine, with labeled schematic/exaggeration and no inferred obstacle data.
- Embed existing calculators; implement subnet inspector without enumerating addresses or starting network activity.
- Add offline articles/charts with source links and metric interpretation limits.
- Run targeted/full tests, seven-page desktop smoke and rendered-image review; record remaining spatial phases.

Completed phase A. Verification: 296 source tests passed; seven-page desktop smoke and all 11 calculator checks passed. Fresnel/curvature screenshots visually inspected. Review identified embedded QDialog Escape behavior; suppressed accept/reject in embedded mode and added a passing keyboard regression. Narrow-window tests caught and verified a reference selector width correction. Original source-linked references are bundled as text. Installer has not been rebuilt for this increment. Approved phases B–D remain pending.
