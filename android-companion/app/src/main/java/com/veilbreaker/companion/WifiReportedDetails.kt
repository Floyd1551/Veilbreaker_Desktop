package com.veilbreaker.companion

/** Presentation of Android-reported ScanResult fields, with no security or coverage inference. */
object WifiReportedDetails {
    fun width(width: Int?, center0: Int?, center1: Int?): String {
        val title = when (width) {
            0 -> "20 MHz"; 1 -> "40 MHz"; 2 -> "80 MHz"; 3 -> "160 MHz"
            4 -> "80+80 MHz"; 5 -> "320 MHz"; else -> return "Not exposed"
        }
        if (width == 0) return title
        fun frequency(value: Int?) = value?.takeIf { it in 1..100_000 }?.let { "$it MHz" }
        val first = frequency(center0)
        if (width != 4) return "$title · " + (first?.let { "center $it" } ?: "center not exposed")
        val second = frequency(center1)
        return when {
            first != null && second != null -> "$title · centers $first / $second"
            first != null -> "$title · first center $first · second center not exposed"
            second != null -> "$title · first center not exposed · second center $second"
            else -> "$title · segment centers not exposed"
        }
    }

    /** An empty or generic string does not prove a network is open or safe. */
    fun security(capabilities: String?): String? = capabilities
        ?.map { if (it.isISOControl()) ' ' else it }?.joinToString("")
        ?.trim()?.takeIf { it.isNotEmpty() }?.take(180)
}
