package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class BasemapCameraTest {
    @Test fun emptyPointsDoNotMoveCamera() {
        assertNull(BasemapCamera.fit(emptyList(), 400, 300))
    }
    @Test fun polarPointsCannotBeProjectedOnStreetMap() {
        assertNull(BasemapCamera.fit(listOf(90.0 to 0.0), 400, 300))
    }
    @Test fun singlePointCentersAtStreetZoom() {
        val c = BasemapCamera.fit(listOf(34.73 to -86.59), 400, 300)!!
        assertEquals(34.73, c.latitude, 0.000001)
        assertEquals(-86.59, c.longitude, 0.000001)
        assertEquals(16, c.zoom)
    }
    @Test fun nearbyPointsStraddlingDatelineUseShortArc() {
        val c = BasemapCamera.fit(listOf(0.0 to 179.9, 0.0 to -179.9), 400, 300)!!
        assertTrue(kotlin.math.abs(c.longitude) > 179.0)
        assertTrue(c.zoom >= 8)
    }
    @Test fun fitAvoidsZoomingBeyondViewport() {
        val c = BasemapCamera.fit(listOf(10.0 to -100.0, 40.0 to -80.0), 400, 300)!!
        val a = WebMercator.project(10.0, -100.0, c.zoom)
        val b = WebMercator.project(40.0, -80.0, c.zoom)
        assertTrue(kotlin.math.abs(a.first - b.first) <= 336)
        assertTrue(kotlin.math.abs(a.second - b.second) <= 236)
    }
}
