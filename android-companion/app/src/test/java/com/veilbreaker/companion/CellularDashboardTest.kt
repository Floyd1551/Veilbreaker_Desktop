package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class CellularDashboardTest {
    private fun cell(id: String = "123", age: Any = 100, value: Any = -95, radio: String = "LTE") =
        JSONObject().put("radio", radio).put("registered", true).put("connection_status", "primary")
            .put("age_ms", age).put("identity", JSONObject().put("mcc", "311").put("mnc", "480").put("cell_id", id))
            .put("signal", JSONObject().put(if (radio == "NR") "ss_rsrp" else "rsrp", JSONObject().put("value", value).put("unit", "dBm")))

    private fun observation(elapsed: Long, vararg cells: JSONObject) = JSONObject()
        .put("subscription_key", "sim-1").put("received_utc", "2026-10-30T10:00:00Z")
        .put("elapsed_realtime_ms", elapsed).put("cells", JSONArray(cells.toList()))

    private fun capture(vararg obs: JSONObject) = JSONObject().put("observations", JSONArray(obs.toList()))

    @Test fun latestServingReadingsAndTrendRespectModemTimeAndCachedDuplicates() {
        val input = capture(observation(10000,cell(age=100,value=-100)), observation(15000,cell(age=5100,value=-100)),
                            observation(20000,cell(age=100,value=-90)))
        val original = input.toString()
        val card = CellularDashboard.build(input).single()
        assertEquals(-90.0, card.metrics.first().value!!, 0.01)
        assertEquals(listOf(9900L,19900L), card.trend.map { it.elapsedMs })
        assertEquals(listOf(-100.0,-90.0), card.trend.map { it.value })
        assertEquals(original, input.toString())
    }

    @Test fun noConflationOfCellsOrUnknownSampleAge() {
        val input = capture(observation(10000,cell(id="old",value=-70)),
            observation(15000,cell(id="new",age=JSONObject.NULL,value=-98)),
            observation(20000,cell(id="new",value=-100)))
        val card = CellularDashboard.build(input).single()
        assertEquals(listOf(-100.0), card.trend.map { it.value })
        assertTrue(card.context.contains("cell new"))
    }

    @Test fun missingValuesAndInvalidUnitsAreNotGraphedOrGuessed() {
        val row=cell(value=JSONObject.NULL)
        row.getJSONObject("signal").put("rsrq", JSONObject().put("value", -10).put("unit", "dBm"))
        val card=CellularDashboard.build(capture(observation(10000,row))).single()
        assertNull(card.metrics[0].value)
        assertNull(card.metrics[1].value)
        assertEquals(0,card.trend.size)
    }

    @Test fun conflictingValuesAtSameModemTimeAreExcluded() {
        val input = capture(observation(10000,cell(age=100,value=-100)), observation(15000,cell(age=5100,value=-80)),
                            observation(20000,cell(age=100,value=-90)))
        assertEquals(listOf(-90.0),CellularDashboard.build(input).single().trend.map { it.value })
    }

    @Test fun doesNotGraphUnidentifiedOrAmbiguousCells() {
        val one=cell();one.getJSONObject("identity").put("cell_id",JSONObject.NULL)
        assertTrue(CellularDashboard.build(capture(observation(10000,one))).single().trend.isEmpty())
        assertTrue(CellularDashboard.build(capture(observation(10000,cell(),cell()))).first().trend.isEmpty())
    }

    @Test fun noRegisteredCellsMeansNoDashboardCards() {
        val row=cell();row.put("registered",false)
        assertTrue(CellularDashboard.build(capture(observation(10000,row))).isEmpty())
        assertTrue(CellularDashboard.build(JSONObject().put("observations", JSONArray())).isEmpty())
    }
}
