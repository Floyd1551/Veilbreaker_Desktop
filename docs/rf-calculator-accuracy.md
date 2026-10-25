# RF calculator accuracy audit

October 25, 2026. Scope: all 11 selectable calculators (three power conversion directions and eight other tools). Software verification, not calibration against field instruments.

## References and independent checks

- [NIST SI defining constants](https://www.nist.gov/pml/special-publication-330/sp-330-section-2): exact vacuum light speed 299792458 m/s and Boltzmann constant 1.380649e-23 J/K.
- [ITU-R P.525-5](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.525-5-202411-I!!PDF-E.pdf): free-space attenuation. Tests use the alternative MHz/km logarithmic form with 32.44778322188338 dB constant. The familiar 32.4 engineering approximation differs by about 0.048 dB; that rounding difference is not a defect.
- [ITU-R P.526-16](https://www.itu.int/dms_pubrec/itu-r/rec/p/R-REC-P.526-16-202511-I!!PDF-E.pdf): Fresnel geometry. Tests additionally check endpoint symmetry, maximum radius at midpoint, inverse square-root frequency scaling and square-root distance scaling.
- [Analog Devices noise-figure analysis](https://www.analog.com/en/resources/technical-articles/system-noisefigure-analysis-for-modern-radio-receivers.html): equivalent receiver noise temperature and the 290 K noise-figure reference. Tests include non-290 K source temperature, zero receiver noise figure, 1 Hz reference noise and bandwidth doubling.
- Power conversion: independently tabulated decade anchors and round trips through watts/milliwatts.
- EIRP and link budget: independent linear power multiplication/division checks dB arithmetic, plus zero/positive/negative margin cases.
- Earth bulge: independent exact spherical midpoint sagitta comparisons at 1, 10 and 100 km, for geometric and 4/3 effective radius. A relative tolerance of 6 parts per million covers the small-angle approximation over the supported range; this is mathematical approximation error, not terrain accuracy.
- Cable loss: zero-loss conservation, decade power ratios and cascaded feed sections.

Numeric reference tests generally use 8–11 decimal places or relative tolerance appropriate to the rounded reference. Such precision verifies arithmetic; it does not imply comparable real-world prediction accuracy.

## Input and result coverage

Every registered field is checked for missing values, nonnumeric types, booleans, NaN, infinities and out-of-range values. Documented endpoints are exercised with compatible path geometry. Path endpoints and out-of-path positions are rejected separately. All default outputs must be finite and JSON serializable; snapshots must be independent of subsequent input mutation.

Every calculator is exercised through the UI and compared with its calculation snapshot. Copy and JSON export must preserve that snapshot. Checks cover stale-result invalidation, search preserving unchanged-tool inputs, empty search results, text exports, save cancellation, I/O failure and extension-free filenames.

## Applicability limits retained

- Free-space calculations require far-field conditions. A nonnegative result alone does not validate the antenna-dependent far-field distance.
- Fresnel uses the standard paraxial radius approximation. The audit identified that unusual low-frequency/short-path combinations could silently give large geometric errors. The calculator now compares with exact first-ellipsoid geometry and warns in the UI and exported limitations when the radius differs by more than 1%. This threshold is a software warning policy, not an ITU certification criterion. The terrain profile engine still uses its documented approximation; this new applicability warning applies to the standalone calculator.
- Curvature uses a spherical small-angle model. A 4/3 factor is an assumption, not measured atmospheric refraction.
- Thermal noise uses the classical kTB model and equivalent noise bandwidth. It is not a measurement of interference and is not a quantum-noise model.
- Extremely large cable losses can underflow the delivered-power percentage to floating-point zero; the logarithmic loss remains available. No measurement precision is implied.
- Source data, cable specifications, antenna pattern, terrain resolution and receiver sensitivity remain operator responsibilities. The audit does not validate a particular installation or promise service availability.

## Execution

`python -m unittest discover -s tests -p test_rf*.py` runs the expanded RF group, including pre-existing RF workflow tests. `python -m unittest discover -s tests` runs the complete application suite. Test results for this audit are recorded in the commit's verification note below.

Final verification: **291 application tests passed**, including **31 RF-group tests**. Added 15 test methods, with parameterized checks covering all 11 calculators and 28 input-field occurrences. The six-page desktop smoke passed. Independent review identified the Fresnel applicability issue and confirmed the warning fix; no other actionable calculation defects were found. No hardware calibration or installer rebuild was performed.
