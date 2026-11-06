package com.veilbreaker.companion

import kotlin.math.max
import kotlin.math.sqrt

/** Shared scale for a schematic comparison, not a map or propagation model. */
internal object WifiPlanningGeometry {
    data class Shapes(val floorSideFraction: Double, val apDiameterFraction: Double)

    fun fromInputs(areaM2: Double, radiusM: Double): Shapes? {
        if (!areaM2.isFinite() || !radiusM.isFinite() || areaM2 <= 0 || radiusM <= 0) return null
        val floorSide = sqrt(areaM2)
        val diameter = 2.0 * radiusM
        if (!floorSide.isFinite() || !diameter.isFinite()) return null
        val largest = max(floorSide, diameter)
        return Shapes(floorSide / largest, diameter / largest)
    }
}
