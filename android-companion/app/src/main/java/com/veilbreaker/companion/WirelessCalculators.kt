package com.veilbreaker.companion

import kotlin.math.log10
import kotlin.math.pow

/** Offline numbering/radio-power arithmetic. These values are not measurements or channel authorization. */
object WirelessCalculators {
    enum class Band { GHZ_24, GHZ_5, GHZ_6 }

    /** AOSP's channel-number frequency raster; presence on the raster does not mean a legal channel. */
    fun channelToMhz(band: Band, channel: Int): Int? = when (band) {
        Band.GHZ_24 -> when (channel) { in 1..13 -> 2407 + 5 * channel; 14 -> 2484; else -> null }
        Band.GHZ_5 -> if (channel in 32..177) 5000 + 5 * channel else null
        Band.GHZ_6 -> when (channel) { 2 -> 5935; in 1..233 -> 5950 + 5 * channel; else -> null }
    }

    /** Reject off-grid frequencies and the special 6 GHz channel 2's non-existent 5960 MHz mapping. */
    fun mhzToChannel(band: Band, mhz: Int): Int? = when (band) {
        Band.GHZ_24 -> when { mhz == 2484 -> 14; mhz in 2412..2472 && (mhz - 2407) % 5 == 0 -> (mhz - 2407) / 5; else -> null }
        Band.GHZ_5 -> if (mhz in 5160..5885 && (mhz - 5000) % 5 == 0) (mhz - 5000) / 5 else null
        Band.GHZ_6 -> when { mhz == 5935 -> 2; mhz in 5955..7115 && mhz != 5960 && (mhz - 5950) % 5 == 0 -> (mhz - 5950) / 5; else -> null }
    }

    fun dbmToMw(dbm: Double): Double? {
        if (!dbm.isFinite()) return null
        val mw = 10.0.pow(dbm / 10.0)
        return mw.takeIf { it.isFinite() && it > 0.0 }
    }

    fun mwToDbm(mw: Double): Double? = if (mw.isFinite() && mw > 0.0) 10.0 * log10(mw) else null
}
