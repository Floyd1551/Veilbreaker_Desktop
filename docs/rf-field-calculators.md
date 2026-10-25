# RF field calculators

Open **Tools & readiness → RF field calculators**. These tools work offline and do not start a capture or contact a device.

Search or select a calculator, enter values in the labeled units, then choose **Calculate**. **Copy result with inputs** includes the calculation version, values, method and limitations. Editing an input clears the previous result. Decimal-point numbers and scientific notation are accepted; invalid or out-of-range values produce a field-specific message.

Available tools:

- Power conversion between dBm, milliwatts and watts.
- Wavelength and ideal quarter-wavelength in meters.
- Free-space path loss using frequency in MHz and distance in km.
- EIRP from transmitter power, transmit cable/connector loss and antenna gain in dBi.
- One-way link budget and margin above a specified receiver sensitivity, including receive antenna gain, feed loss and additional losses.
- First Fresnel zone radius and 60% clearance guide at an interior path point.
- Earth bulge for geometric Earth and an explicit 4/3 effective-radius assumption (paths up to 100 km).
- Thermal noise and input-referred receiver noise using bandwidth, source temperature and receiver noise figure.
- Cable/feed loss from length, manufacturer attenuation at the operating frequency and total connector loss.

Results are calculated estimates, not sensor readings. Free-space loss excludes obstacles and does not establish LOS. Positive link margin does not guarantee service or availability. Receiver sensitivity must correspond to the intended bandwidth and modulation/rate. Quarter-wave length is not a finished antenna design. EIRP calculations do not check regulatory limits.

Use **Save result…** to export a UTF-8 text report or JSON snapshot before closing. The export includes inputs, units, results, calculator version, method and limitations. Results appear before inputs for easier reading. Saving calculations directly into survey points remains planned; exported calculations do not change diagnostic evidence.

Fresnel and Earth-bulge tools share the terrain engine's geometry, but do not receive terrain elevations or obstacle heights. They cannot determine whether a real path is clear. The noise calculator excludes interference; noise figure uses a 290 K reference and is converted to equivalent receiver noise temperature when the source temperature differs. Cable attenuation must be supplied for the frequency being assessed.

The standalone Fresnel calculator warns when its paraxial approximation differs from exact first-ellipsoid geometry by more than 1%, which can occur on short paths at low frequencies. Do not use a warned result for clearance decisions. See the [accuracy audit](rf-calculator-accuracy.md) for reference methods, tests and applicability limits.
