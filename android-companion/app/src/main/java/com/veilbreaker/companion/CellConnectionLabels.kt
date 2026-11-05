package com.veilbreaker.companion

/** Public Android telephony constants, kept independent from Android for testability. */
object CellConnectionLabels {
    fun radio(type: Int): String = when (type) {
        0 -> "Not exposed"; 1 -> "GPRS"; 2 -> "EDGE"; 3 -> "UMTS"; 4 -> "CDMA"
        5 -> "EV-DO 0"; 6 -> "EV-DO A"; 7 -> "1xRTT"; 8 -> "HSDPA"; 9 -> "HSUPA"
        10 -> "HSPA"; 11 -> "iDEN"; 12 -> "EV-DO B"; 13 -> "LTE"; 14 -> "eHRPD"
        15 -> "HSPA+"; 16 -> "GSM"; 17 -> "TD-SCDMA"; 18 -> "IWLAN"; 19 -> "LTE CA"
        20 -> "NR (5G)"; else -> "Android type $type"
    }
    fun dataState(state: Int): String = when (state) {
        0 -> "Disconnected"; 1 -> "Connecting"; 2 -> "Connected"; 3 -> "Suspended"; 4 -> "Disconnecting"
        else -> "Not exposed"
    }
}
