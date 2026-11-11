package com.veilbreaker.companion

/** Response age uses Android's monotonic clock; it is not the modem sample age. */
object LiveCellFreshness {
    fun describe(receivedElapsedMs: Long?, nowElapsedMs: Long): String? {
        if (receivedElapsedMs == null || receivedElapsedMs < 0 || nowElapsedMs < receivedElapsedMs) return null
        val seconds = (nowElapsedMs - receivedElapsedMs) / 1000
        return "Response received $seconds s ago. Modem sample age is shown at receipt; the response may be cached."
    }
}
