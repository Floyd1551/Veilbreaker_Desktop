package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class LiveCellSummaryTest {
    private fun cell(registered: Boolean, role: String, age: Any, power: Any) = JSONObject()
        .put("radio", "LTE").put("registered", registered).put("connection_status", role).put("age_ms", age)
        .put("identity", JSONObject().put("pci", 12).put("bands", JSONArray().put(2)))
        .put("signal", JSONObject().put("rsrp", JSONObject().put("value", power).put("unit", "dBm")))

    @Test fun exposesServingRoleAgeAndMissingMeasurementsWithoutInventingThem() {
        val text = LiveCellSummary.render(listOf(cell(true, "none", 42000, JSONObject.NULL)), JSONObject().put("ranges", JSONArray()))
        assertTrue(text.contains("Registered"))
        assertTrue(text.contains("42000 ms old at receipt"))
        assertTrue(text.contains("RSRP: Not exposed"))
        assertTrue(text.contains("B2 (modem reported)"))
        assertFalse(text.contains("Primary serving"))
    }

    @Test fun prioritizesServingAndCountsOmittedNeighbors() {
        val neighbors = (1..15).map { cell(false, "none", 0, -100) }
        val result = LiveCellSummary.render(neighbors + cell(true, "primary", 5, -86), JSONObject().put("ranges", JSONArray()))
        assertTrue(result.indexOf("Primary serving") < result.indexOf("Neighbor"))
        assertTrue(result.contains("6 more"))
    }

    @Test fun emptyDoesNotClaimNoCoverage() {
        val result = LiveCellSummary.render(emptyList(), JSONObject().put("ranges", JSONArray()))
        assertTrue(result.contains("No cells reported"))
        assertFalse(result.contains("no coverage"))
    }
}
