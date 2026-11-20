package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class GnssSkyModelTest {
    private fun satellite(az: Float, el: Float, used: Boolean = false) =
        LiveGpsSummary.Satellite("GPS", 4, used, 30f, el, az)

    @Test fun cardinalDirectionsAndElevationAreProjectedCorrectly() {
        val frame = GnssSkyModel.frame(listOf(satellite(0f, 0f, true), satellite(90f, 0f),
            satellite(180f, 0f), satellite(270f, 0f), satellite(360f, 90f)), 1000L, 1000L, true)
        assertEquals(GnssSkyModel.State.READY, frame.state)
        val expected = listOf(0.0 to -1.0, 1.0 to 0.0, 0.0 to 1.0, -1.0 to 0.0, 0.0 to 0.0)
        frame.points.zip(expected).forEach { (point, xy) ->
            assertEquals(xy.first, point.x, 1e-6); assertEquals(xy.second, point.y, 1e-6)
        }
        assertTrue(frame.points[0].used)
    }

    @Test fun invalidAnglesAreNotPlacedAndVisibleCountsAreTruthful() {
        val rows = listOf(satellite(Float.NaN, 20f), satellite(20f, Float.NaN), satellite(-1f, 30f),
            satellite(361f, 30f), satellite(20f, -1f), satellite(20f, 91f), satellite(45f, 45f))
        val frame = GnssSkyModel.frame(rows, 1000L, 1000L, true)
        assertEquals(GnssSkyModel.State.READY, frame.state)
        assertEquals(1, frame.points.size); assertEquals(6, frame.omitted)
        assertEquals(GnssSkyModel.State.NO_POSITIONS,
            GnssSkyModel.frame(rows.dropLast(1), 1000L, 1000L, true).state)
    }

    @Test fun waitingEmptyUnavailableAndStaleAreNotDrawnAsCurrentPositions() {
        assertEquals(GnssSkyModel.State.UNAVAILABLE, GnssSkyModel.frame(null, null, 1000, false).state)
        assertEquals(GnssSkyModel.State.WAITING, GnssSkyModel.frame(null, null, 1000, true).state)
        assertEquals(GnssSkyModel.State.EMPTY, GnssSkyModel.frame(emptyList(), 1000, 1000, true).state)
        val stale = GnssSkyModel.frame(listOf(satellite(45f, 30f)), 1000, 11001, true)
        assertEquals(GnssSkyModel.State.STALE, stale.state); assertTrue(stale.points.isEmpty())
        assertEquals(GnssSkyModel.State.STALE, GnssSkyModel.frame(listOf(satellite(0f, 0f)), 1001, 1000, true).state)
    }

    @Test fun pointCountIsBounded() {
        val result = GnssSkyModel.frame(List(300) { satellite(0f, 0f) }, 1000, 1000, true)
        assertEquals(256, result.points.size); assertEquals(44, result.omitted)
    }
}
