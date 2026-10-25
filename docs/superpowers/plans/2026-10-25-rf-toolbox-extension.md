# RF toolbox extension

Execute inline with test-driven development, continuing the user-approved toolbox roadmap.

Scope: first Fresnel radius and 60% clearance at a selected interior path point; geometric/4:3 Earth bulge; thermal noise and input-referred receiver noise; cable/feed loss. Reuse `terrain_profile.assess_profile` for geometric computations. Add UTF-8 text/JSON snapshot exports with input labels, method and limitations. Results first in the display. No sensor or LOS claims, and no survey mutation.

- Write and observe failing numeric and invalid-position tests.
- Extend registry and calculations, preserving existing tool behavior.
- Test snapshot exports and stale-result protection before UI changes.
- Add Save result with native file chooser and visible I/O errors.
- Run targeted tests, terrain regression tests and desktop smoke; update user documentation.

Completed: all steps. Verification: 276 source tests passed; all 9 targeted toolbox tests passed after export-path refinement; 2 terrain profile tests passed; six-page desktop smoke passed. Rendered Fresnel dialog inspected with Windows fonts. Independent review reported no actionable issues. No installer rebuilt; direct survey attachment remains a separate increment.
