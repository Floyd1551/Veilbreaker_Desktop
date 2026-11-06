package com.veilbreaker.companion

import kotlin.math.*

/** Operator-input planning arithmetic. None of these models represent measured coverage or discovered topology. */
object PlanningModels {
    data class Wifi(val areaCount: Int, val capacityCount: Int, val startingCount: Int)
    data class Fwa(val distanceKm: Double, val bearingDegrees: Double, val freeSpaceLossDb: Double)
    data class Topology(val nodes: List<String>, val links: List<Pair<Int, Int>>)

    fun wifi(areaM2: Double, idealRadiusM: Double, clients: Int, clientsPerAp: Int): Wifi? {
        if (!areaM2.isFinite() || !idealRadiusM.isFinite() || areaM2 <= 0 || idealRadiusM <= 0 || clients < 0 || clientsPerAp <= 0) return null
        val area = ceil(areaM2 / (PI * idealRadiusM * idealRadiusM))
        val capacity = ceil(clients.toDouble() / clientsPerAp)
        if (!area.isFinite() || area < 1 || area > 100000 || capacity > 100000) return null
        return Wifi(area.toInt(), capacity.toInt(), maxOf(area.toInt(), capacity.toInt()))
    }

    fun fwa(lat1: Double, lon1: Double, lat2: Double, lon2: Double, mhz: Double): Fwa? {
        if (listOf(lat1, lon1, lat2, lon2, mhz).any { !it.isFinite() } || lat1 !in -90.0..90.0 || lat2 !in -90.0..90.0 || lon1 !in -180.0..180.0 || lon2 !in -180.0..180.0 || mhz <= 0.0 || mhz > 1e7) return null
        val phi1 = Math.toRadians(lat1); val phi2 = Math.toRadians(lat2)
        val dPhi = phi2 - phi1; val dLambda = Math.toRadians(lon2 - lon1)
        val a = (sin(dPhi / 2).pow(2) + cos(phi1) * cos(phi2) * sin(dLambda / 2).pow(2)).coerceIn(0.0, 1.0)
        // Initial bearing is undefined for coincident and antipodal points.
        if (a < 1e-16 || a > 1.0 - 1e-14) return null
        val distanceKm = 6371.0088 * 2.0 * atan2(sqrt(a), sqrt(1.0 - a))
        val bearing = (Math.toDegrees(atan2(sin(dLambda) * cos(phi2), cos(phi1) * sin(phi2) - sin(phi1) * cos(phi2) * cos(dLambda))) + 360.0) % 360.0
        val loss = 32.45 + 20.0 * log10(distanceKm) + 20.0 * log10(mhz)
        return Fwa(distanceKm, bearing, loss)
    }

    fun topology(nodeText: String, linkText: String): Topology? {
        val nodes = nodeText.lines().map { it.trim() }.filter { it.isNotEmpty() }
        if (nodes.isEmpty() || nodes.size > 12 || nodes.any { it.length > 24 || it.any(Char::isISOControl) || it.contains('>') } || nodes.toSet().size != nodes.size) return null
        val links = mutableListOf<Pair<Int, Int>>()
        for (line in linkText.lines().map { it.trim() }.filter { it.isNotEmpty() }) {
            val pieces = line.split('>')
            if (pieces.size != 2) return null
            val a = nodes.indexOf(pieces[0].trim()); val b = nodes.indexOf(pieces[1].trim())
            if (a < 0 || b < 0 || a == b || links.size >= 30 || links.any { (it.first == a && it.second == b) || (it.first == b && it.second == a) }) return null
            links.add(a to b)
        }
        return Topology(nodes, links)
    }
}
