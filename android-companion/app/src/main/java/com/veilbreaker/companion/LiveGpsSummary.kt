package com.veilbreaker.companion

import java.util.Locale

/** Formatting of reported GNSS status; no inferred satellite or location data. */
internal object LiveGpsSummary {
    data class Satellite(val constellation: String, val svid: Int, val used: Boolean,
                         val cn0: Float, val elevation: Float, val azimuth: Float)

    fun satellites(rows: List<Satellite>?): String {
        if (rows == null) return "No satellite report received yet."
        val header = "${rows.size} reported · ${rows.count { it.used }} used in last fix"
        if (rows.isEmpty()) return header
        val lines = rows.take(128).map { row ->
            val signal = row.cn0.takeIf { it.isFinite() && it >= 0 }?.let {
                String.format(Locale.US, "%.1f dB-Hz", it)
            } ?: "signal not exposed"
            val angle = if (row.elevation.isFinite() && row.azimuth.isFinite())
                String.format(Locale.US, " · elevation %.0f° · azimuth %.0f°", row.elevation, row.azimuth) else ""
            "${row.constellation} ${row.svid} · ${if (row.used) "used" else "not used"} · $signal$angle"
        }
        return (listOf(header) + lines + if (rows.size > 128) listOf("Additional entries omitted.") else emptyList()).joinToString("\n")
    }
}
