package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiPlanningGeometryTest {
    @Test fun comparesSquareAndDiameterAtOneSharedScale() {
        val same = WifiPlanningGeometry.fromInputs(100.0, 5.0)!!
        assertEquals(1.0, same.floorSideFraction, 1e-12)
        assertEquals(1.0, same.apDiameterFraction, 1e-12)

        val largerFloor = WifiPlanningGeometry.fromInputs(1600.0, 5.0)!!
        assertEquals(1.0, largerFloor.floorSideFraction, 1e-12)
        assertEquals(0.25, largerFloor.apDiameterFraction, 1e-12)

        val largerFootprint = WifiPlanningGeometry.fromInputs(25.0, 5.0)!!
        assertEquals(0.5, largerFootprint.floorSideFraction, 1e-12)
        assertEquals(1.0, largerFootprint.apDiameterFraction, 1e-12)
    }

    @Test fun rejectsInvalidAndOverflowingInputs() {
        assertNull(WifiPlanningGeometry.fromInputs(Double.NaN, 5.0))
        assertNull(WifiPlanningGeometry.fromInputs(0.0, 5.0))
        assertNull(WifiPlanningGeometry.fromInputs(100.0, -1.0))
        assertNull(WifiPlanningGeometry.fromInputs(100.0, Double.MAX_VALUE))
    }
}
