package com.veilbreaker.companion

/** Display helpers. Channel numbers are derived from frequency, not a regulatory band plan. */
object WifiSnapshotFormat {
    /** Legacy connectionInfo is not tied to a selected Network; never mix them. */
    fun <T> association(networkSelected: Boolean, bound: T?, legacy: () -> T?): T? =
        if (networkSelected) bound else legacy()

    fun channel(mhz: Int): Int? = when {
        mhz == 2484 -> 14
        mhz in 2412..2472 && (mhz - 2412) % 5 == 0 -> (mhz - 2407) / 5
        mhz in 5005..5895 && (mhz - 5000) % 5 == 0 -> (mhz - 5000) / 5
        mhz == 5935 -> 2
        mhz in 5955..7115 && (mhz - 5950) % 5 == 0 -> (mhz - 5950) / 5
        else -> null
    }

    fun ssid(value: String?): String? {
        val clean = value?.trim()?.removeSurrounding("\"") ?: return null
        if (clean.isEmpty() || clean.equals("<unknown ssid>", true) || clean.equals("unknown ssid", true)) return null
        return clean.map { if (it.isISOControl()) ' ' else it }.joinToString("").take(128)
    }

    fun bssid(value: String?): String? {
        val clean = value?.trim()?.lowercase() ?: return null
        if (clean == "02:00:00:00:00:00" || clean == "00:00:00:00:00:00" ||
            !Regex("[0-9a-f]{2}(:[0-9a-f]{2}){5}").matches(clean)) return null
        return clean
    }

    /** ScanResult.timestamp is microseconds since boot; receiptMs is elapsed realtime. */
    fun ageSeconds(receiptMs: Long, scanTimestampUs: Long): Long? {
        if (receiptMs < 0 || scanTimestampUs <= 0) return null
        val sampleMs = scanTimestampUs / 1000
        if (sampleMs > receiptMs || (sampleMs == receiptMs && scanTimestampUs % 1000 != 0L)) return null
        return (receiptMs - sampleMs) / 1000
    }
}
