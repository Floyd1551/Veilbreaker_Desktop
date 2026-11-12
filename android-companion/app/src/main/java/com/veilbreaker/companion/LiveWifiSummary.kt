package com.veilbreaker.companion

/** Present an Android Wi-Fi connection without substituting redacted values. */
object LiveWifiSummary {
    data class Details(val status: String, val name: String, val signal: String,
                       val channel: String, val frequency: String, val linkRate: String, val available: Boolean)

    fun details(enabled: Boolean, present: Boolean, isDefault: Boolean, permission: Boolean,
                ssid: String?, rssi: Int?, frequencyMhz: Int?, linkRateMbps: Int?): Details {
        val status = when {
            !enabled -> "Wi-Fi off"
            !present -> "No Wi-Fi network reported"
            !permission -> "Location permission required for connection details"
            isDefault -> "Default Wi-Fi network"
            else -> "Wi-Fi connected · not default network"
        }
        val visible = enabled && present && permission
        val frequency = frequencyMhz?.takeIf { visible && it > 0 }
        return Details(status, if (visible) WifiSnapshotFormat.ssid(ssid) ?: "Name not exposed" else "Not exposed",
            rssi?.takeIf { visible && it > -127 && it <= 0 }?.let { "$it dBm" } ?: "Not exposed",
            frequency?.let { WifiSnapshotFormat.channel(it)?.toString() } ?: "Not exposed",
            frequency?.let { "$it MHz" } ?: "Not exposed",
            linkRateMbps?.takeIf { visible && it > 0 }?.let { "$it Mbps" } ?: "Not exposed", visible)
    }
    fun format(enabled: Boolean, present: Boolean, isDefault: Boolean, permission: Boolean,
               ssid: String?, rssi: Int?, frequencyMhz: Int?, linkRateMbps: Int?): String {
        if (!enabled) return "Wi-Fi off · Android reports no active Wi-Fi radio."
        if (!present) return "No Wi-Fi network reported by Android."
        if (!permission) return "Wi-Fi present · location permission is required for connection details. Granting permission does not record GPS."
        val name = WifiSnapshotFormat.ssid(ssid) ?: "Network name not exposed / redacted"
        val signal = rssi?.takeIf { it > -127 && it <= 0 }?.let { "$it dBm" } ?: "Signal not exposed"
        val channel = frequencyMhz?.takeIf { it > 0 }?.let { freq ->
            val number = WifiSnapshotFormat.channel(freq)
            if (number == null) "$freq MHz · channel unknown" else "Channel $number (derived) · $freq MHz"
        } ?: "Frequency not exposed"
        val speed = linkRateMbps?.takeIf { it > 0 }?.let { "$it Mbps" } ?: "not exposed"
        return "${if (isDefault) "Default Wi-Fi" else "Wi-Fi present · not the default network"}\n$name\n$signal · $channel\nLink rate $speed · negotiated, not measured throughput\nAndroid system values; sample age not exposed."
    }
}
