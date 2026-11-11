package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class LiveCellMetricsTest {
    private fun cell(role: String, registered: Boolean = true) = JSONObject()
        .put("radio", "LTE").put("registered", registered).put("connection_status", role).put("age_ms", 2500)
        .put("identity", JSONObject().put("pci", 12).put("bands", JSONArray().put(2)))
        .put("signal", JSONObject().put("rsrp", JSONObject().put("value", -88).put("unit", "dBm")))

    @Test fun selectsOnePrimaryAndRetainsMissingFieldsAndSampleAge() {
        val source = cell("primary"); val before = source.toString()
        val card = LiveCellMetrics.build(listOf(cell("none", false), source), JSONObject().put("ranges", JSONArray()))!!
        assertEquals("LTE · Primary serving", card.title)
        assertEquals(-88.0, card.values[0].value!!, 0.0)
        assertNull(card.values[1].value)
        assertTrue(card.age.contains("2500 ms old at receipt"))
        assertEquals(before, source.toString())
    }

    @Test fun avoidsGuessingWhenServingRoleIsAmbiguous() {
        val plan = JSONObject().put("ranges", JSONArray())
        assertNull(LiveCellMetrics.build(listOf(cell("none"), cell("none")), plan))
        assertNull(LiveCellMetrics.build(listOf(cell("primary"), cell("primary")), plan))
        assertNull(LiveCellMetrics.build(listOf(cell("none", false)), plan))
        assertNotNull(LiveCellMetrics.build(listOf(cell("none")), plan))
    }
}
