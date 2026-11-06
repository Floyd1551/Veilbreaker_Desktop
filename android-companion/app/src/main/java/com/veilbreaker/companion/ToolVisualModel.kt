package com.veilbreaker.companion

/** Display metadata only; these schematic drawings are never captured evidence. */
internal object ToolVisualModel {
    enum class Kind { FRESNEL, EARTH, RF_PATH, CHAIN, OPTICAL, POWER, WAVE, REFLECTION, NETWORK, NOISE, WIFI_RASTER }
    data class Spec(val kind: Kind, val description: String)

    fun forTool(id: String): Spec? = when (id) {
        "fresnel" -> Spec(Kind.FRESNEL, "The radius is evaluated at a point between A and B. The lens is a conceptual first Fresnel zone, not a terrain profile or clearance result.")
        "bulge", "horizon" -> Spec(Kind.EARTH, "The curved Earth and straight path are exaggerated. This diagram is not a terrain profile and does not establish line of sight.")
        "fspl", "density" -> Spec(Kind.RF_PATH, "An ideal free-space path between endpoints. The diagram omits terrain, obstacles, antenna patterns and reflections.")
        "link", "eirp", "erp", "coax", "lossstack", "fade" -> Spec(Kind.CHAIN, "Illustrative power flow: source, gains and losses, then destination. Stages are conceptual; use the entered values and units for the calculation.")
        "fiberloss", "fiberbudget" -> Spec(Kind.OPTICAL, "Illustrative optical path with a source, fiber and receiver. Real connector, splice, splitter and fiber losses depend on the actual installation.")
        "poe", "runtime" -> Spec(Kind.POWER, "Illustrative power flow from a source to a load. The calculation uses the operator's entered values and does not measure actual delivery.")
        "wavelength", "quarterwave" -> Spec(Kind.WAVE, "One conceptual wave cycle. Wavelength depends on propagation speed; the calculator uses free-space speed.")
        "mismatch", "returnloss", "reflected" -> Spec(Kind.REFLECTION, "Conceptual incident and reflected waves at an impedance mismatch. This figure is not an instrument measurement or a cable-loss model.")
        "bdp", "tcpwindow", "serialization", "propdelay", "mss4", "mss6" -> Spec(Kind.NETWORK, "Conceptual data path between endpoints. Values come from entered packet, link or timing assumptions, not a network test.")
        "thermal", "snr" -> Spec(Kind.NOISE, "Conceptual signal and noise contributions. Bar heights are illustrative, not calibrated or measured power.")
        "wifi24", "wifi5", "wifi6" -> Spec(Kind.WIFI_RASTER, "Ticks show example channel center frequencies only. They do not show channel width, activity, interference, or authorization. The 2.4 GHz channel 14 and 6 GHz channel 2 are special cases.")
        else -> null
    }

    /** Relative path position using distances from each endpoint. Invalid values have no marker. */
    fun pathFraction(distanceA: Double, distanceB: Double): Float? {
        if (!distanceA.isFinite() || !distanceB.isFinite() || distanceA <= 0 || distanceB <= 0) return null
        // Divide first so even very large finite values cannot overflow the sum.
        val fraction = if (distanceA >= distanceB) 1.0 / (1.0 + distanceB / distanceA)
            else (distanceA / distanceB) / (1.0 + distanceA / distanceB)
        return fraction.toFloat().coerceIn(0f, 1f)
    }
}
