package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class CellularGaugeLayoutTest {
    @Test fun narrowOrLargeFontUsesStackedGauges() {
        assertTrue(CellularGaugeLayout.stacked(320, 1.0f))
        assertTrue(CellularGaugeLayout.stacked(360, 1.0f))
        assertTrue(CellularGaugeLayout.stacked(600, 1.3f))
        assertTrue(CellularGaugeLayout.stacked(600, Float.NaN))
        assertFalse(CellularGaugeLayout.stacked(600, 1.0f))
    }
}
