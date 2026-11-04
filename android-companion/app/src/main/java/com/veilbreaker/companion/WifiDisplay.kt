package com.veilbreaker.companion

/** Presentation helpers: meters are display scales, not a quality or coverage claim. */
object WifiDisplay {
    fun barPercent(rssi: Int?): Int? {
        if (rssi == null || rssi <= -127 || rssi > 0) return null
        return ((rssi.coerceIn(-120, -30) + 120) * 100 / 90)
    }

    fun channelText(frequency: Int?): String {
        if (frequency == null || frequency <= 0) return "Frequency unavailable"
        val channel = WifiSnapshotFormat.channel(frequency)
        return "Channel ${channel ?: "unknown"}${if (channel == null) "" else " (derived)"} · $frequency MHz"
    }

    fun ageText(ageSeconds: Long?): String =
        if (ageSeconds == null || ageSeconds < 0) "Age unavailable" else "$ageSeconds s old at view"
}
