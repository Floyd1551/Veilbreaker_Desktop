package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class FwaCapturePickerTest {
    private fun quantity(value: Any, unit: String) = JSONObject().put("value", value).put("unit", unit)
    private fun cell(radio: String, signal: JSONObject, id: String) = JSONObject().put("radio", radio)
        .put("registered", true).put("connection_status", "primary").put("identity", JSONObject().put("cell_id", id))
        .put("signal", signal).put("age_ms", 250)
    private fun obs(elapsed: Int, vararg cells: JSONObject) = JSONObject().put("subscription_key", "sim-1")
        .put("observation_id", "obs-$elapsed").put("elapsed_realtime_ms", elapsed).put("received_utc", "2026-11-06T10:00:00Z")
        .put("cells", JSONArray(cells.toList()))
    @Test fun latestCellsKeepTheirOwnMeasurementsAndProvenance() {
        val old = cell("LTE", JSONObject().put("rsrp", quantity(-110, "dBm")), "old")
        val lte = cell("LTE", JSONObject().put("rsrp", quantity(-100, "dBm")).put("rsrq", quantity(-9, "dB")), "123")
        val nr = cell("NR", JSONObject().put("ss_sinr", quantity(12, "dB")), "456")
        val capture = JSONObject().put("capture_id", "capture-1").put("observations", JSONArray(listOf(obs(1, old), obs(2, lte, nr))))
        val before = capture.toString()
        val result = FwaCapturePicker.options(capture).candidates
        assertEquals(2, result.size)
        assertEquals(-100.0, result[0].rsrp!!, 0.0)
        assertNull(result[0].sinr)
        assertNull(result[1].rsrp)
        assertEquals(12.0, result[1].sinr!!, 0.0)
        assertTrue(result[0].description.contains("capture-1"))
        assertTrue(result[0].description.contains("obs-2"))
        assertTrue(result[0].description.contains("123"))
        assertEquals(before, capture.toString())
    }
    @Test fun missingOrInvalidValuesAreNotInvented() {
        val bad = cell("LTE", JSONObject().put("rsrp", quantity(-100, "dB")).put("rsrq", quantity(999, "dB")), "123")
        assertTrue(FwaCapturePicker.options(JSONObject().put("observations", JSONArray().put(obs(1, bad)))).candidates.isEmpty())
        assertTrue(FwaCapturePicker.options(null).candidates.isEmpty())
    }
    @Test fun differentKnownCaptureIdentitySuppressesCellularComparison() {
        val a = FwaCapturePicker.Context("a", mapOf("radio" to "LTE", "cell_id" to "123", "subscription" to "sim-1"))
        val b = FwaCapturePicker.Context("b", mapOf("radio" to "NR", "cell_id" to "456", "subscription" to "sim-1"))
        assertFalse(FwaCapturePicker.comparable(a, b))
        assertTrue(FwaCapturePicker.comparable(a, FwaCapturePicker.Context("unknown", emptyMap())))
        assertTrue(FwaCapturePicker.comparable(a, null))
        val first = FwaCapturePicker.Candidate(a, -100.0, -10.0, 4.0)
        val second = FwaCapturePicker.Candidate(b, -90.0, -8.0, 8.0)
        val baseline = FwaTuning.sample("first", 0.0, -100.0, -10.0, 4.0, 10.0, null, first)!!
        val trial = FwaTuning.sample("second", 5.0, -90.0, -8.0, 8.0, 20.0, null, second)!!
        val diff = FwaTuning.difference(baseline, trial)
        assertNull(diff.rsrp); assertNull(diff.rsrq); assertNull(diff.sinr)
        assertEquals(10.0, diff.downlink!!, 0.0)
    }
}
