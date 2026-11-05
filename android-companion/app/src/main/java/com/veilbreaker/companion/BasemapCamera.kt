package com.veilbreaker.companion

/** Derive a bounded map camera from evidence points without changing those points. */
object BasemapCamera {
    data class Camera(val latitude: Double, val longitude: Double, val zoom: Int)
    fun fit(points: List<Pair<Double, Double>>, width: Int, height: Int): Camera? {
        val valid = points.filter { it.first.isFinite() && it.second.isFinite() && it.first in -85.05112878..85.05112878 && it.second in -180.0..180.0 }
        if (valid.isEmpty() || width <= 0 || height <= 0) return null
        val projected = valid.map { WebMercator.project(it.first, it.second, 0) }
        val anchor = projected.first().first
        val world = WebMercator.worldSize(0)
        val xs = projected.map { anchor + WebMercator.wrappedDelta(it.first, anchor, world) }
        val ys = projected.map { it.second }
        val minX = xs.minOrNull()!!; val maxX = xs.maxOrNull()!!
        val minY = ys.minOrNull()!!; val maxY = ys.maxOrNull()!!
        val usableW = maxOf(1, width - 64).toDouble(); val usableH = maxOf(1, height - 64).toDouble()
        var zoom = 16
        while (zoom > 2 && ((maxX - minX) * (1 shl zoom) > usableW || (maxY - minY) * (1 shl zoom) > usableH)) zoom--
        val center = WebMercator.unproject((minX + maxX) / 2.0, (minY + maxY) / 2.0, 0)
        return Camera(center.first, center.second, zoom)
    }
}
