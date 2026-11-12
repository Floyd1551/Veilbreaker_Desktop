package com.veilbreaker.companion

/** Derived navigation and field prompts; these never turn reference values into evidence. */
internal object ReferenceReaderModel {
    fun valueReference(id: String): String? = when (id) {
        "wifi-rssi" -> "Example design target: Cisco's deployment guidance for specific IP phones uses at least −67 dBm and 25 dB SNR. This is a device/workload-specific design example, not a universal pass/fail value. Verify client and service requirements.\nSource: Cisco IP Phone Multiplatform Wireless LAN Deployment Guide, section on RF coverage. https://spg.xgslb-v3.cisco.com/c/dam/en/us/td/docs/voice_ip_comm/cuipph/MPP/common/WIFI-Deployment-guide/MPP-wlan-dg.pdf"
        "cell-power" -> "Android API reporting ranges, not service targets:\nLTE RSRP: −140 to −43 dBm\nNR SS-RSRP: −156 to −31 dBm\nUnreported values remain unavailable. Device, network and deployment context govern interpretation.\nSources: https://developer.android.com/reference/android/telephony/CellSignalStrengthLte and https://developer.android.com/reference/android/telephony/CellSignalStrengthNr"
        "cell-quality" -> "Android API reporting ranges, not service targets:\nLTE RSSNR: −20 to +30 dB\nNR SS-SINR: −23 to +40 dB\nNR SS-RSRQ: −43 to +20 dB\nCompare only like metrics; unavailable is not zero.\nSources: https://developer.android.com/reference/android/telephony/CellSignalStrengthLte and https://developer.android.com/reference/android/telephony/CellSignalStrengthNr"
        else -> null
    }
    fun checks(entry: WirelessReferenceLibrary.Entry): List<String> {
        val terms = (entry.tags + entry.title).joinToString(" ").lowercase(java.util.Locale.ROOT)
        val specific = when {
            "fresnel" in terms || "terrain" in terms -> "Are antenna heights, obstacles, frequency and the assumed propagation model documented?"
            "rsrp" in terms || "sinr" in terms || "rsrq" in terms -> "Are power and quality readings from the same technology, cell and comparable times?"
            "ssid" in terms || "bssid" in terms || "roam" in terms -> "Are the network identity, client and observation time known, and was a service interruption actually observed?"
            "channel" in terms || "airtime" in terms -> "Are the band, channel width and collection method known, and is utilization measured rather than inferred from a scan?"
            "fiber" in terms || "optical" in terms -> "Are the wavelength, equipment limits, path components and measurement method documented?"
            "poe" in terms || "power" in terms && entry.category == "Fiber & Power" -> "Are source and device ratings, cable path and peak load known?"
            "noise" in terms || "sdr" in terms -> "Are receiver settings, bandwidth and calibration known, and is the value measured or calculated?"
            "subnet" in terms || "cidr" in terms || "dns" in terms -> "Are the relevant interface, address, prefix, target and resolver recorded?"
            else -> "Which values were observed directly, and which were entered, calculated or obtained from a reference?"
        }
        return listOf(specific, "What information is missing, and what comparable follow-up measurement would reduce uncertainty?")
    }
    fun recordPrompt(entry: WirelessReferenceLibrary.Entry): String = when (entry.category) {
        "Wi-Fi" -> "Record the client, network identity when exposed, band, channel, location and observation time. Note whether a value is a cached scan, a connected-link value or an actual service test."
        "Cellular" -> "Record the selected SIM, technology, carrier, cell identity, band, sample age and location when available. Keep signal power, quality and service-test results separate."
        "RF" -> "Record frequency, receiver and antenna, settings, location and time. Mark values as measured, entered or calculated, and keep calibration and assumptions visible."
        "Networking" -> "Record the interface, target, address or prefix, time and test method. Compare equivalent paths and distinguish observed results from configuration."
        "Fiber & Power" -> "Record equipment and ratings, operating conditions, measurement method and units. Identify entered specifications separately from observed readings."
        "Guides" -> "Record the objective, equipment, test locations, time, results and missing data. Preserve assumptions and repeat conditions when comparing changes."
        else -> "Record source, time, method, units and limitations alongside any field observation."
    }

    fun related(entry: WirelessReferenceLibrary.Entry): List<WirelessReferenceLibrary.Entry> {
        val tags = entry.tags.map { it.lowercase(java.util.Locale.ROOT) }.toSet()
        return WirelessReferenceLibrary.entries.asSequence().filter { it.id != entry.id }
            .map { candidate ->
                val overlap = candidate.tags.count { it.lowercase(java.util.Locale.ROOT) in tags }
                candidate to (overlap * 10 + if (candidate.category == entry.category) 1 else 0)
            }.filter { it.second > 0 }
            .sortedWith(compareByDescending<Pair<WirelessReferenceLibrary.Entry, Int>> { it.second }.thenBy { it.first.title })
            .take(3).map { it.first }.toList()
    }
}
