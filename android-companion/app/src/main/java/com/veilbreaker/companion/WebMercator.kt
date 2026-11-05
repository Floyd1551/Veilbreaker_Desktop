package com.veilbreaker.companion

import kotlin.math.PI
import kotlin.math.atan
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.ln
import kotlin.math.sinh
import kotlin.math.tan

/** Web Mercator / XYZ projection used for the optional street basemap. */
object WebMercator {
    const val TILE_SIZE = 256
    private const val MAX_LATITUDE = 85.0511287798066
    private const val MAX_VIEWPORT = 8192

    /** x is the wrapped tile address; displayX retains the unwrapped world copy. */
    data class Tile(val x: Int, val y: Int, val displayX: Int)

    fun worldSize(zoom: Int): Double {
        require(zoom in 0..22) { "Zoom must be between 0 and 22." }
        return TILE_SIZE.toDouble() * (1 shl zoom)
    }

    fun project(lat: Double, lon: Double, zoom: Int): Pair<Double, Double> {
        require(lat.isFinite() && lon.isFinite()) { "Coordinates must be finite." }
        val size = worldSize(zoom)
        val longitude = ((lon % 360.0 + 180.0) % 360.0 + 360.0) % 360.0 - 180.0
        val radians = Math.toRadians(lat.coerceIn(-MAX_LATITUDE, MAX_LATITUDE))
        val x = (longitude + 180.0) / 360.0 * size
        val y = ((1.0 - ln(tan(PI / 4.0 + radians / 2.0)) / PI) / 2.0 * size).coerceIn(0.0, size)
        return x to y
    }

    fun unproject(x: Double, y: Double, zoom: Int): Pair<Double, Double> {
        require(x.isFinite() && y.isFinite()) { "Coordinates must be finite." }
        val size = worldSize(zoom)
        val normalizedX = ((x % size) + size) % size
        val latitude = Math.toDegrees(atan(sinh(PI * (1.0 - 2.0 * y.coerceIn(0.0, size) / size))))
        return latitude to (normalizedX / size * 360.0 - 180.0)
    }

    /** Shortest signed horizontal distance from b to a, across the dateline. */
    fun wrappedDelta(a: Double, b: Double, world: Double): Double {
        require(a.isFinite() && b.isFinite() && world.isFinite() && world > 0.0)
        val d = (a - b) % world
        return when { d < -world / 2.0 -> d + world; d >= world / 2.0 -> d - world; else -> d }
    }

    /** Only tiles intersecting the current viewport; no background or neighboring prefetch. */
    fun visibleTiles(centerX: Double, centerY: Double, zoom: Int, width: Int, height: Int): List<Tile> {
        val size = worldSize(zoom)
        require(centerX.isFinite() && centerY.isFinite() && kotlin.math.abs(centerX) < 1e10 && kotlin.math.abs(centerY) < 1e10)
        require(width in 0..MAX_VIEWPORT && height in 0..MAX_VIEWPORT)
        if (width == 0 || height == 0) return emptyList()
        val firstX = floor((centerX - width / 2.0) / TILE_SIZE).toInt()
        val lastX = (ceil((centerX + width / 2.0) / TILE_SIZE) - 1).toInt()
        val firstY = floor((centerY - height / 2.0) / TILE_SIZE).toInt().coerceAtLeast(0)
        val lastY = (ceil((centerY + height / 2.0) / TILE_SIZE) - 1).toInt().coerceAtMost((size / TILE_SIZE).toInt() - 1)
        if (firstY > lastY) return emptyList()
        val columns = (size / TILE_SIZE).toInt()
        return buildList {
            for (y in firstY..lastY) for (displayX in firstX..lastX) {
                add(Tile(Math.floorMod(displayX, columns), y, displayX))
            }
        }
    }
}
