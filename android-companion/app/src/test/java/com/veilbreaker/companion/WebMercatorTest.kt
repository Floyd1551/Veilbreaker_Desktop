package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WebMercatorTest {
    @Test fun equatorAndGreenwichAreAtWorldCenter() {
        val p = WebMercator.project(0.0, 0.0, 3)
        assertEquals(1024.0, p.first, 0.00001)
        assertEquals(1024.0, p.second, 0.00001)
    }
    @Test fun projectionClampsLatitudeAndNormalizesLongitude() {
        val a = WebMercator.project(90.0, 180.0, 2)
        assertEquals(0.0, a.first, 0.00001)
        assertEquals(0.0, a.second, 0.001)
        val b = WebMercator.unproject(a.first, a.second, 2)
        assertEquals(85.05112878, b.first, 0.00001)
    }
    @Test fun centerRoundTripAndWrappedDistance() {
        val p = WebMercator.project(34.73, -86.59, 15)
        val q = WebMercator.unproject(p.first, p.second, 15)
        assertEquals(34.73, q.first, 0.000001)
        assertEquals(-86.59, q.second, 0.000001)
        assertEquals(-10.0, WebMercator.wrappedDelta(5.0, 15.0, 1024.0), 0.00001)
        assertEquals(10.0, WebMercator.wrappedDelta(5.0, 1019.0, 1024.0), 0.00001)
    }
    @Test fun visibleTilesAreBoundedAndWrapAtDateline() {
        val tiles = WebMercator.visibleTiles(0.0, 128.0, 1, 256, 256)
        assertEquals(setOf(0, 1), tiles.map { it.x }.toSet())
        assertTrue(tiles.all { it.y in 0..1 })
        assertTrue(tiles.size <= 4)
    }
    @Test fun tileBoundariesDoNotFetchAdjacentTiles() {
        assertEquals(listOf(WebMercator.Tile(0, 0, 0)), WebMercator.visibleTiles(128.0, 128.0, 2, 256, 256))
    }
    @Test fun wrappedTilesPreserveDisplayColumn() {
        val tiles = WebMercator.visibleTiles(0.0, 128.0, 1, 256, 256)
        assertEquals(listOf(WebMercator.Tile(1, 0, -1), WebMercator.Tile(0, 0, 0)), tiles)
    }
    @Test fun noTilesBeyondPolarExtentOrForEmptyViewport() {
        assertTrue(WebMercator.visibleTiles(0.0, -1000.0, 2, 256, 256).isEmpty())
        assertTrue(WebMercator.visibleTiles(0.0, 0.0, 2, 0, 256).isEmpty())
    }
    @Test fun rejectsNonFiniteCoordinatesAndUnboundedInputs() {
        assertThrows(IllegalArgumentException::class.java) { WebMercator.project(Double.NaN, 0.0, 1) }
        assertThrows(IllegalArgumentException::class.java) { WebMercator.visibleTiles(0.0, 0.0, 23, 256, 256) }
        assertThrows(IllegalArgumentException::class.java) { WebMercator.visibleTiles(0.0, 0.0, 1, 8193, 256) }
    }
}
