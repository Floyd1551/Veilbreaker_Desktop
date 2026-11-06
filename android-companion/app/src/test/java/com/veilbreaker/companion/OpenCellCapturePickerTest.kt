package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class OpenCellCapturePickerTest {
    private fun cell(radio: String, registered: Boolean, id: JSONObject) = JSONObject()
        .put("radio", radio).put("registered", registered).put("identity", id)
    private fun id(mcc: String = "311", mnc: String = "480", tac: Any = 12, cellId: String = "456") = JSONObject()
        .put("mcc", mcc).put("mnc", mnc).put("tac", tac).put("cell_id", cellId)
    private fun obs(sub: String, elapsed: Long, vararg rows: JSONObject) = JSONObject()
        .put("subscription_key", sub).put("elapsed_realtime_ms", elapsed).put("received_utc", "2026-11-06T10:00:00Z")
        .put("cells", JSONArray(rows.toList()))
    private fun capture(vararg rows: JSONObject) = JSONObject().put("observations", JSONArray(rows.toList()))

    @Test fun latestPerSubscriptionAndRegisteredCellsOnly() {
        val old = obs("sim-1", 1, cell("LTE", true, id(cellId = "999")))
        val newer = obs("sim-1", 2, cell("LTE", true, id()), cell("NR", true, id(cellId = "12345678901")), cell("LTE", false, id(cellId = "777")))
        val other = obs("sim-2", 3, cell("LTE", true, id(mnc = "01")))
        val data = capture(old, newer, other); val before = data.toString()
        val options = OpenCellCapturePicker.options(data)
        assertEquals(3, options.candidates.size)
        assertEquals(listOf("456", "12345678901", "456"), options.candidates.map { it.cellId })
        assertEquals("01", options.candidates.last().mnc)
        assertEquals(before, data.toString())
    }

    @Test fun missingAndInvalidIdentityIsNeverFilledFromAnotherCell() {
        val valid = cell("LTE", true, id())
        val missingTac = cell("NR", true, id().removeField("tac"))
        val invalid = cell("LTE", true, id(cellId = "-1"))
        val options = OpenCellCapturePicker.options(capture(obs("sim-1", 5, valid, missingTac, invalid)))
        assertEquals(1, options.candidates.size)
        assertEquals(2, options.incomplete)
        assertEquals("456", options.candidates.single().cellId)
    }

    @Test fun malformedOrMissingObservationsDoNotInventCandidates() {
        assertTrue(OpenCellCapturePicker.options(null).candidates.isEmpty())
        val invalid = JSONObject().put("subscription_key", "sim").put("cells", JSONArray().put(cell("LTE", true, id())))
        assertTrue(OpenCellCapturePicker.options(capture(invalid)).candidates.isEmpty())
    }

    private fun JSONObject.removeField(key: String): JSONObject = apply { remove(key) }
}
