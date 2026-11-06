package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class PlanningModelsTest {
    @Test fun wifiUsesCapacityAndIdealCircularArea() {
        val model = PlanningModels.wifi(1000.0, 10.0, 100, 25)!!
        assertEquals(4, model.areaCount)
        assertEquals(4, model.capacityCount)
        assertEquals(4, model.startingCount)
        assertEquals(5, PlanningModels.wifi(100.0, 10.0, 101, 25)!!.startingCount)
        assertNull(PlanningModels.wifi(1000.0, 0.0, 2, 1))
        assertNull(PlanningModels.wifi(Double.NaN, 10.0, 2, 1))
        assertNull(PlanningModels.wifi(1000.0, 10.0, 2, 0))
        assertNull(PlanningModels.wifi(1e100, 1.0, 2, 1))
    }
    @Test fun fwaDistanceBearingAndLoss() {
        val model = PlanningModels.fwa(0.0, 0.0, 0.0, 1.0, 1000.0)!!
        assertEquals(111.195, model.distanceKm, 0.01)
        assertEquals(90.0, model.bearingDegrees, 0.001)
        assertEquals(133.32, model.freeSpaceLossDb, 0.1)
        val dateline = PlanningModels.fwa(0.0, 179.0, 0.0, -179.0, 1000.0)!!
        assertEquals(222.39, dateline.distanceKm, 0.1)
        assertEquals(90.0, dateline.bearingDegrees, 0.001)
        assertNull(PlanningModels.fwa(91.0, 0.0, 0.0, 1.0, 1000.0))
        assertNull(PlanningModels.fwa(0.0, 0.0, 0.0, 0.0, 1000.0))
        assertNull(PlanningModels.fwa(0.0, 0.0, 0.0, 1.0, Double.NaN))
        assertNull(PlanningModels.fwa(0.0, 0.0, 0.0, 1.0, 0.0))
        assertNull(PlanningModels.fwa(0.0, 0.0, 0.0, 180.0, 1000.0))
    }
    @Test fun topologyValidatesLinksAndDuplicateNodes() {
        val graph = PlanningModels.topology("Gateway\nSwitch\nAP", "Gateway > Switch\nSwitch > AP")!!
        assertEquals(3, graph.nodes.size)
        assertEquals(2, graph.links.size)
        assertNull(PlanningModels.topology("Gateway\nGateway", ""))
        assertNull(PlanningModels.topology("Gateway\nAP", "Gateway > Unknown"))
        assertNull(PlanningModels.topology("Gateway\nAP", "Gateway > Gateway"))
        assertNull(PlanningModels.topology("Gateway\nAP", "Gateway > AP\nAP > Gateway"))
        assertNull(PlanningModels.topology("", ""))
    }
}
