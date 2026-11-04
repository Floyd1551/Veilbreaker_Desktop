package com.veilbreaker.companion

/** Use full-width gauges when three columns would crowd scaled text. */
object CellularGaugeLayout {
    fun stacked(screenWidthDp: Int, fontScale: Float): Boolean =
        screenWidthDp < 420 || !fontScale.isFinite() || fontScale > 1.15f
}
