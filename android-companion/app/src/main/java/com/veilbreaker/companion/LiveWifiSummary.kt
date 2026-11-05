package com.veilbreaker.companion

/** Present an Android Wi-Fi connection without substituting redacted values. */
object LiveWifiSummary {
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
