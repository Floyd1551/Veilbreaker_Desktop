package com.veilbreaker.companion

import java.util.Locale

/** Curated local field notes. Sources are provenance links; lookup never uses the network. */
object WirelessReferenceLibrary {
    data class Entry(
        val id: String,
        val category: String,
        val title: String,
        val summary: String,
        val fieldUse: String,
        val limitations: String,
        val sourceName: String,
        val sourceUrl: String,
        val reviewed: String,
        val tags: List<String> = emptyList()
    ) {
        val searchableText: String get() = listOf(category, title, summary, fieldUse, limitations, sourceName, *tags.toTypedArray()).joinToString(" ").lowercase(Locale.ROOT)
    }
    private const val REVIEWED = "2026-11-05"
    private const val WIFI = "https://developer.android.com/reference/android/net/wifi/WifiInfo"
    private const val LTE = "https://developer.android.com/reference/android/telephony/CellSignalStrengthLte"
    private const val NR = "https://developer.android.com/reference/android/telephony/CellSignalStrengthNr"
    private const val P2040 = "https://www.itu.int/rec/R-REC-P.2040/en"
    val categories = listOf("All", "Wi-Fi", "Cellular", "RF", "Networking", "Fiber & Power", "Guides")
    val entries = listOf(
        Entry("wifi-rssi", "Wi-Fi", "Wi-Fi signal and RSSI",
            "RSSI is the received signal strength reported for a Wi-Fi link, commonly shown in dBm. Values closer to zero indicate more received power.",
            "Compare readings at repeatable locations and orientation. Check quality, retries and actual service performance alongside signal strength.",
            "RSSI alone does not measure interference or prove a healthy connection. Android can return the strongest associated link for multi-link operation and fields may be unavailable or redacted.",
            "Android WifiInfo API", WIFI, REVIEWED, listOf("signal", "rssi", "mlo", "power")),
        Entry("wifi-rate", "Wi-Fi", "Link rate and throughput",
            "Wi-Fi link speed is the current negotiated physical-layer rate, not application throughput.",
            "When a transfer is slow, compare link rate with a timed test to a known target, and record test direction and whether the path is Wi-Fi or cellular.",
            "Airtime sharing, protocol overhead, retransmissions, congestion, server and backhaul limits affect throughput. A short download is not sustained capacity.",
            "Android WifiInfo API", WIFI, REVIEWED, listOf("phy", "rate", "speed", "network test")),
        Entry("wifi-identity", "Wi-Fi", "SSID, BSSID and roaming",
            "An SSID is a network name; BSSID identifies a basic service set. Several access points can share a name.",
            "Record the BSSID, band/channel and receipt time when comparing observations. A changing BSSID may indicate roaming or a different link.",
            "Permissions, Android version, hardware and multi-link operation can limit or change the reported identity. An SSID alone does not identify an individual AP.",
            "Android WifiInfo API", WIFI, REVIEWED, listOf("ssid", "bssid", "ap", "roam", "access point")),
        Entry("wifi-channels", "Wi-Fi", "Channels, bandwidth and overlap",
            "A channel number describes a frequency position; channel width describes a span. Wider channels can overlap more neighboring spectrum.",
            "Compare channel, width, visible neighbors and connection performance; investigate contention before assuming that a stronger signal fixes the issue.",
            "Nearby scan results can be cached or incomplete and do not establish airtime utilization. Legal channels and power depend on country, equipment and current rules.",
            "Android ScanResult API", "https://developer.android.com/reference/android/net/wifi/ScanResult", REVIEWED, listOf("2.4 ghz", "5 ghz", "6 ghz", "channel", "bandwidth")),
        Entry("cell-power", "Cellular", "RSRP and SS-RSRP",
            "LTE RSRP and NR SS-RSRP indicate power in their respective reference signals, reported in dBm when the phone exposes them.",
            "Compare observations on the same technology, cell and band with quality measurements and sample age. LTE and NR reference definitions are not interchangeable.",
            "Phone modem APIs can omit, cache or round values. Stronger reference power alone does not prove usable throughput or identify a physical tower.",
            "Android LTE signal API; NR API: $NR", LTE, REVIEWED, listOf("rsrp", "ss-rsrp", "lte", "5g", "nr", "power")),
        Entry("cell-quality", "Cellular", "RSRQ and SINR",
            "RSRQ and SINR describe different aspects of radio quality. SINR compares signal with interference plus noise; LTE and NR expose their own metrics.",
            "A strong signal paired with poor quality is a useful reason to investigate interference, load or path conditions and compare repeat tests.",
            "A reading cannot identify the actual interferer or prove congestion. No universal threshold applies to every radio, workload and deployment; missing is not zero.",
            "Android LTE signal API", LTE, REVIEWED, listOf("rsrq", "sinr", "rssnr", "ss-sinr", "ss-rsrq", "quality")),
        Entry("cell-identity", "Cellular", "Cell identity, PCI and towers",
            "A PCI is a radio identity used locally and is reused across a network; a cellular identifier is not a verified physical tower coordinate.",
            "Record the carrier, technology, cell identity, band and time together. Treat any tower match as a candidate until separately verified.",
            "A DAS can use a shared cell identity across multiple remote antennas. Phone reports may omit fields and cannot establish the physical antenna serving a point.",
            "Android CellIdentityLte API", "https://developer.android.com/reference/android/telephony/CellIdentityLte", REVIEWED, listOf("pci", "eci", "nci", "tower", "das", "antenna")),
        Entry("rf-power", "RF", "dB, dBm and antenna gain",
            "dB represents a ratio; dBm is power relative to one milliwatt. Antenna gain in dBi is referenced to an isotropic antenna.",
            "For power ratios, +3.01 dB is approximately double and +10 dB is ten times. A link budget adds gain and subtracts losses in consistent units.",
            "An entered or calculated power is not a measurement. Antenna pattern, direction, mismatch and both ends of the link matter.",
            "ITU-R P.525-5 (2024) free-space propagation", "https://www.itu.int/rec/R-REC-P.525/en", REVIEWED, listOf("db", "dbm", "dbi", "mw", "power", "gain", "eirp")),
        Entry("rf-noise", "RF", "Thermal noise and bandwidth",
            "At 290 K, ideal matched thermal noise is approximately −174 dBm/Hz. Estimate noise as −174 + 10 log10(bandwidth in Hz) dBm.",
            "For a 20 MHz equivalent noise bandwidth, this is about −101 dBm before receiver noise figure. Add noise figure for a simple input-referred estimate.",
            "This is calculated context, not a measured SDR noise floor. Noise bandwidth, temperature, interference and implementation matter.",
            "Keysight noise figure measurement application note", "https://www.keysight.com/us/en/assets/7018-06808/application-notes/5952-8255.pdf", "2026-10-30", listOf("noise floor", "thermal", "bandwidth", "receiver", "sdr")),
        Entry("rf-obstacles", "RF", "Obstacles and propagation",
            "Concrete, reinforced structures, metal, glazing and foliage can change a radio path through attenuation, reflection, scattering or diffraction.",
            "Record the obstacle, measurement locations and antenna orientation. Compare repeat observations on either side and consider Fresnel clearance for point-to-point paths.",
            "A signal reading cannot identify a specific cause. Material composition, geometry, frequency and moisture matter; do not assign a universal loss to concrete.",
            "ITU-R P.2040-4 (2025) building materials", P2040, REVIEWED, listOf("concrete", "pillar", "wall", "reflection", "diffraction", "fresnel", "material"))
    ) + ExpandedFieldReferences.entries

    /** All search terms must match; category is an exact, stable display category. */
    fun search(category: String?, query: String): List<Entry> {
        val words = query.trim().lowercase(Locale.ROOT).split(Regex("\\s+")).filter { it.isNotEmpty() }
        return entries.filter { entry ->
            val expanded = ReferenceReaderModel.expanded(entry).joinToString(" ") { (title, body) -> "$title $body" }.lowercase(Locale.ROOT)
            val searchable = entry.searchableText + " " + expanded
            (category.isNullOrBlank() || category == "All" || entry.category == category) && words.all(searchable::contains)
        }
    }
}
