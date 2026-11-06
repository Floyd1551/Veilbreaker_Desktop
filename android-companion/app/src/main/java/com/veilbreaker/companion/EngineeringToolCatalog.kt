package com.veilbreaker.companion

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.log10
import kotlin.math.pow
import kotlin.math.sqrt

/** Calculations use operator inputs; outputs are estimates, never collected evidence. */
object EngineeringToolCatalog {
    data class Tool(
        val id: String, val title: String, val category: String, val description: String,
        val fields: List<String>, val unit: String, val formula: (List<Double>) -> Double?
    ) {
        fun evaluate(values: List<Double>): Double? {
            if (values.size != fields.size || values.any { !it.isFinite() }) return null
            return runCatching { formula(values)?.takeIf(Double::isFinite) }.getOrNull()
        }
    }

    private fun tool(id: String, title: String, category: String, description: String,
                     unit: String, vararg fields: String, formula: (List<Double>) -> Double?) =
        Tool(id, title, category, description, fields.toList(), unit, formula)
    private fun positive(vararg n: Double) = n.all { it > 0 }
    private fun nonnegative(vararg n: Double) = n.all { it >= 0 }
    private fun whole(n: Double) = n >= 0 && n == kotlin.math.floor(n)
    private fun gamma(swr: Double) = (swr - 1) / (swr + 1)

    // Units and limitations are shown with each tool, rather than hidden behind inferred defaults.
    val tools: List<Tool> = listOf(
        tool("dbmtomw", "dBm to mW", "RF", "Convert absolute RF power referenced to 1 mW; calculated power is not a measurement.", "mW", "Power (dBm)") { v -> WirelessCalculators.dbmToMw(v[0]) },
        tool("mwtodbm", "mW to dBm", "RF", "Convert positive power in mW to dBm; calculated power is not a measurement.", "dBm", "Power (mW)") { v -> WirelessCalculators.mwToDbm(v[0]) },
        tool("wifi24", "WiFi 2.4 GHz channel to frequency", "Wi-Fi", "Channel-numbering grid only; not a list of authorized or valid primary channels. Channel 14 is a special case.", "MHz", "Channel number") { v ->
            if (!whole(v[0]) || v[0] > Int.MAX_VALUE) null else WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_24, v[0].toInt())?.toDouble()
        },
        tool("wifi5", "WiFi 5 GHz channel to frequency", "Wi-Fi", "Channel-numbering grid only; it does not determine authorization, channel width or DFS requirements.", "MHz", "Channel number") { v ->
            if (!whole(v[0]) || v[0] > Int.MAX_VALUE) null else WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_5, v[0].toInt())?.toDouble()
        },
        tool("wifi6", "WiFi 6 GHz channel to frequency", "Wi-Fi", "Channel-numbering grid only, including the channel 2 special case; it does not establish authorization.", "MHz", "Channel number") { v ->
            if (!whole(v[0]) || v[0] > Int.MAX_VALUE) null else WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_6, v[0].toInt())?.toDouble()
        },
        tool("fspl", "Free-space path loss", "RF", "Ideal unobstructed far-field path between isotropic antennas; excludes terrain, reflections and atmospheric loss. ITU-R P.525.", "dB", "Frequency (MHz)", "Path distance (km)") { v ->
            if (!positive(v[0], v[1])) null else 32.45 + 20 * log10(v[0]) + 20 * log10(v[1])
        },
        tool("wavelength", "Frequency to wavelength", "RF", "Free-space wavelength; propagation in a cable or material is slower.", "m", "Frequency (MHz)") { v ->
            if (!positive(v[0])) null else 299.792458 / v[0]
        },
        tool("quarterwave", "Quarter-wave element", "RF", "Ideal free-space quarter wavelength. Real antennas need end-effect and velocity-factor adjustments.", "m", "Frequency (MHz)") { v ->
            if (!positive(v[0])) null else 299.792458 / v[0] / 4
        },
        tool("eirp", "EIRP", "RF", "Transmitter power plus antenna gain minus feed loss; enter gain in dBi and loss as positive dB.", "dBm", "Transmitter power (dBm)", "Antenna gain (dBi)", "Feed loss (dB)") { v ->
            if (!nonnegative(v[2])) null else v[0] + v[1] - v[2]
        },
        tool("erp", "EIRP to ERP", "RF", "ERP is referenced to an ideal half-wave dipole, 2.15 dB below EIRP.", "dBm ERP", "EIRP (dBm)") { v -> v[0] - 2.15 },
        tool("link", "RF received power budget", "RF", "Predicted power = transmit power + antenna gains − feed loss − path loss. Include other losses in path loss.", "dBm", "Transmitter power (dBm)", "Transmit gain (dBi)", "Total feed loss (dB)", "Path loss (dB)", "Receive gain (dBi)") { v ->
            if (!nonnegative(v[2], v[3])) null else v[0] + v[1] - v[2] - v[3] + v[4]
        },
        tool("thermal", "Thermal noise floor", "RF", "Approximation at 290 K: −174 dBm/Hz + 10 log₁₀(bandwidth in Hz) + noise figure. Ignores external noise.", "dBm", "Bandwidth (MHz)", "Receiver noise figure (dB)") { v ->
            if (!positive(v[0]) || !nonnegative(v[1])) null else -174.0 + 10 * log10(v[0] * 1_000_000) + v[1]
        },
        tool("snr", "Signal to noise ratio", "RF", "Subtract noise power from signal-only power in the same bandwidth. Do not use total signal-plus-noise RSSI as signal-only power; interference is excluded.", "dB", "Signal-only power (dBm)", "Noise power (dBm)") { v -> v[0] - v[1] },
        tool("fade", "Link fade margin", "RF", "Predicted receive power minus receiver sensitivity. A positive value is not a guarantee of availability.", "dB", "Receive power (dBm)", "Sensitivity (dBm)") { v -> v[0] - v[1] },
        tool("fresnel", "First Fresnel zone radius", "RF", "First-zone radius at a point between antennas. Distances must be positive; not a terrain-clearance assessment.", "m", "Frequency (MHz)", "Distance from end A (km)", "Distance from end B (km)") { v ->
            if (!positive(v[0], v[1], v[2])) null else sqrt((299.792458 / v[0]) * (v[1] * 1000) * (v[2] * 1000) / ((v[1] + v[2]) * 1000))
        },
        tool("bulge", "Earth bulge", "RF", "Approximate effective Earth bulge between endpoints, using operator-supplied k factor; not measured terrain.", "m", "Distance from end A (km)", "Distance from end B (km)", "Effective Earth k factor") { v ->
            if (!positive(v[0], v[1], v[2])) null else (v[0] * 1000) * (v[1] * 1000) / (2 * 6_371_000 * v[2])
        },
        tool("horizon", "Radio horizon", "RF", "Small-height approximation for antenna height and effective Earth k factor. Height must be at most 1% of the effective radius. Obstacles and changing refraction are ignored.", "km", "Antenna height (m)", "Effective Earth k factor") { v ->
            if (!nonnegative(v[0]) || !positive(v[1]) || v[0] > 0.01 * 6_371_000 * v[1]) null else sqrt(2 * 6_371_000 * v[1] * v[0]) / 1000
        },
        tool("coax", "Coax cable loss", "RF", "Scale a manufacturer's attenuation at the selected frequency by cable length. Excludes connectors.", "dB", "Cable length (ft)", "Loss at frequency (dB per 100 ft)") { v ->
            if (!nonnegative(v[0], v[1])) null else v[0] * v[1] / 100
        },
        tool("lossstack", "RF loss stack", "RF", "Sum three entered passive component losses. Include all components and frequency-specific values.", "dB", "Loss A (dB)", "Loss B (dB)", "Loss C (dB)") { v ->
            if (!nonnegative(*v.toDoubleArray())) null else v.sum()
        },
        tool("mismatch", "Mismatch loss from VSWR", "RF", "Ideal single-interface mismatch loss. Assumes real reference impedance and ignores cable loss.", "dB", "VSWR (at least 1)") { v ->
            if (v[0] < 1) null else -10 * log10(1 - gamma(v[0]).pow(2))
        },
        tool("returnloss", "Return loss from VSWR", "RF", "Return loss = −20 log₁₀(|Γ|); perfect 1:1 match has infinite return loss and is not numeric.", "dB", "VSWR (greater than 1)") { v ->
            if (v[0] <= 1) null else -20 * log10(gamma(v[0]))
        },
        tool("reflected", "Reflected power from VSWR", "RF", "Ideal reflected fraction at one impedance mismatch; this is not a cable-loss estimate.", "%", "VSWR (at least 1)") { v ->
            if (v[0] < 1) null else gamma(v[0]).pow(2) * 100
        },
        tool("polarization", "Polarization mismatch", "RF", "Ideal linear-to-linear polarization loss. A 90° ideal null tends to infinity; real environments reflect and depolarize.", "dB loss", "Angle difference (degrees, 0 to less than 90)") { v ->
            if (v[0] < 0 || v[0] >= 90) null else -20 * log10(abs(cos(v[0] * PI / 180)))
        },
        tool("doppler", "Doppler shift", "RF", "One-way nonrelativistic approximation, limited to 1% of light speed. Enter the magnitude of radial speed toward or away from the source.", "Hz magnitude", "Frequency (MHz)", "Radial speed magnitude (m/s)") { v ->
            if (!positive(v[0]) || !nonnegative(v[1]) || v[1] > 2_997_924.58) null else v[0] * 1_000_000 * v[1] / 299_792_458
        },
        tool("density", "Far-field power density", "RF", "Ideal free-space power density from EIRP. Far-field assumption only; not an exposure compliance determination.", "W/m²", "EIRP (dBm)", "Distance (m)") { v ->
            if (!positive(v[1])) null else 10.0.pow((v[0] - 30) / 10) / (4 * PI * v[1] * v[1])
        },
        tool("nrscs", "5G NR subcarrier spacing", "Cellular", "Nominal 3GPP numerology: spacing = 15 × 2^μ kHz. A calculated value does not imply band or device support.", "kHz", "Numerology μ (whole number 0–4)") { v ->
            if (!whole(v[0]) || v[0] > 4) null else 15 * 2.0.pow(v[0])
        },
        tool("nrchannel", "NR-ARFCN to frequency", "Cellular", "3GPP global NR raster; center frequency only. Does not identify a band, channel bandwidth or transmit authorization.", "MHz", "NR-ARFCN (whole number)") { v ->
            val n = v[0]
            if (!whole(n) || n > 3_279_165) null else when {
                n <= 599_999 -> n * 0.005
                n <= 2_016_666 -> 3000 + (n - 600_000) * 0.015
                else -> 24250.08 + (n - 2_016_667) * 0.06
            }
        },
        tool("tdd", "TDD downlink duty cycle", "Cellular", "Nominal time share based on operator-entered downlink and total symbols; special/flexible symbols need separate accounting.", "%", "Downlink symbols", "Total symbols") { v ->
            if (!whole(v[0]) || !whole(v[1]) || !positive(v[1]) || v[0] > v[1]) null else 100 * v[0] / v[1]
        },
        tool("mss4", "IPv4 TCP MSS", "Networking", "MTU minus minimum IPv4 and TCP headers (20 bytes each); options and tunnels reduce usable payload.", "bytes", "IP MTU (bytes)") { v -> if (!whole(v[0]) || v[0] <= 40) null else v[0] - 40 },
        tool("mss6", "IPv6 TCP MSS", "Networking", "MTU minus base IPv6 header and minimum TCP header (60 bytes total); extensions, options and tunnels reduce payload.", "bytes", "IP MTU (bytes)") { v -> if (!whole(v[0]) || v[0] <= 60) null else v[0] - 60 },
        tool("bdp", "Bandwidth-delay product", "Networking", "Ideal in-flight data for the entered bandwidth and round-trip time. Real TCP behavior varies.", "bytes", "Bandwidth (Mbps)", "Round-trip time (ms)") { v ->
            if (!positive(v[0]) || !nonnegative(v[1])) null else v[0] * v[1] * 125
        },
        tool("tcpwindow", "TCP window throughput limit", "Networking", "Ideal window/RTT limit for one flow; excludes loss, congestion control, overhead and host limits.", "Mbps", "TCP window (bytes)", "Round-trip time (ms)") { v ->
            if (!positive(v[0], v[1])) null else v[0] * 8 / (v[1] * 1000)
        },
        tool("serialization", "Packet serialization delay", "Networking", "Time to put the entered bytes on the link; excludes queueing, propagation and protocol overhead not included in the byte count.", "ms", "Bytes on wire", "Link rate (Mbps)") { v ->
            if (!positive(v[0], v[1])) null else v[0] * 8 / (v[1] * 1000)
        },
        tool("propdelay", "Cable propagation delay", "Networking", "One-way delay using the stated cable velocity factor; does not include switching or serialization.", "µs", "Cable length (m)", "Velocity factor (0–1)") { v ->
            if (!nonnegative(v[0]) || !positive(v[1]) || v[1] > 1) null else v[0] / (299_792_458 * v[1]) * 1_000_000
        },
        tool("fiberloss", "Fiber path loss", "Fiber & Power", "Fiber attenuation plus total connector and splice loss. Enter actual component values at the chosen wavelength.", "dB", "Fiber length (km)", "Fiber attenuation (dB/km)", "Connector and splice loss (dB)") { v ->
            if (!nonnegative(*v.toDoubleArray())) null else v[0] * v[1] + v[2]
        },
        tool("fiberbudget", "Optical power budget", "Fiber & Power", "Transmit optical power minus receiver sensitivity. Compare with total path loss and required engineering margin.", "dB", "Transmit power (dBm)", "Receiver sensitivity (dBm)") { v -> v[0] - v[1] },
        tool("poe", "PoE remaining budget", "Fiber & Power", "Budget remaining after allocated load; use power available at the same point in the system and account for cable loss.", "W", "Source available (W)", "Allocated load (W)") { v ->
            if (!nonnegative(v[0], v[1])) null else v[0] - v[1]
        },
        tool("runtime", "Battery runtime", "Fiber & Power", "Approximate runtime from usable rated energy and conversion efficiency; aging, temperature and load affect results.", "hours", "Battery energy (Wh)", "Load (W)", "Efficiency (%)") { v ->
            if (!positive(v[0], v[1], v[2]) || v[2] > 100) null else v[0] * v[2] / 100 / v[1]
        }
    )

    fun search(query: String): List<Tool> {
        val words = query.trim().lowercase().split(Regex("\\s+")).filter { it.isNotEmpty() }
        return tools.filter { tool ->
            val haystack = listOf(tool.title, tool.category, tool.description, tool.id).joinToString(" ").lowercase()
            words.all { it in haystack }
        }
    }
}
