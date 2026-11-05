package com.veilbreaker.companion

import org.junit.Assert.assertEquals
import org.junit.Test

class CellConnectionLabelsTest {
    @Test fun radioTypesAreNamedWithoutAssuming5gOverride() {
        assertEquals("LTE", CellConnectionLabels.radio(13))
        assertEquals("NR (5G)", CellConnectionLabels.radio(20))
        assertEquals("Not exposed", CellConnectionLabels.radio(0))
        assertEquals("Android type 100", CellConnectionLabels.radio(100))
    }
    @Test fun dataStatesDoNotPretendToMeasureConnectivity() {
        assertEquals("Connected", CellConnectionLabels.dataState(2))
        assertEquals("Disconnected", CellConnectionLabels.dataState(0))
        assertEquals("Not exposed", CellConnectionLabels.dataState(-1))
    }
}
