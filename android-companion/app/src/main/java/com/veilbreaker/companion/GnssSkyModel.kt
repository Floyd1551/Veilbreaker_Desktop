package com.veilbreaker.companion

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.sin

/** Normalized sky positions from the latest Android satellite report, not measured location evidence. */
internal object GnssSkyModel {
    private const val MAX_ROWS = 256
    private const val MAX_AGE_MS = 10_000L

    enum class State { UNAVAILABLE, WAITING, EMPTY, NO_POSITIONS, READY, STALE }
    data class Point(val x: Double, val y: Double, val used: Boolean, val constellation: String, val svid: Int)
    data class Frame(val state: State, val points: List<Point> = emptyList(), val omitted: Int = 0, val ageMs: Long? = null)

    /** North is up, east is right; horizon is the outer ring and zenith is the centre. */
    fun frame(rows: List<LiveGpsSummary.Satellite>?, receivedMs: Long?, nowMs: Long, available: Boolean): Frame {
        if (!available) return Frame(State.UNAVAILABLE)
        if (rows == null || receivedMs == null) return Frame(State.WAITING)
        if (receivedMs < 0 || nowMs < receivedMs) return Frame(State.STALE)
        val age = nowMs - receivedMs
        if (age > MAX_AGE_MS) return Frame(State.STALE, ageMs = age)
        if (rows.isEmpty()) return Frame(State.EMPTY, ageMs = age)
        val points = rows.take(MAX_ROWS).mapNotNull { row ->
            if (!row.azimuth.isFinite() || !row.elevation.isFinite() ||
                row.azimuth !in 0f..360f || row.elevation !in 0f..90f) return@mapNotNull null
            val angle = row.azimuth.toDouble() * PI / 180.0
            val radius = (90.0 - row.elevation.toDouble()) / 90.0
            Point(radius * sin(angle), -radius * cos(angle), row.used, row.constellation, row.svid)
        }
        return Frame(if (points.isEmpty()) State.NO_POSITIONS else State.READY,
            points = points, omitted = rows.size - points.size, ageMs = age)
    }
}
