package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class LiveOverviewModelTest {
    private fun cell(radio: String, value: Int, role: String = "primary") = JSONObject()
        .put("radio", radio).put("registered", true).put("connection_status", role).put("age_ms", 400)
        .put("identity", JSONObject().put("mcc", "311").put("mnc", "480").put("cell_id", "42").put("pci", 3)
            .put(if (radio == "LTE") "earfcn" else "nrarfcn", if (radio == "LTE") 5230 else 650000))
        .put("signal", JSONObject().put(if (radio == "LTE") "rsrp" else "ss_rsrp",
            JSONObject().put("value", value).put("unit", "dBm")))

    private fun observation(elapsed: Long, cells: JSONArray, location: JSONObject? = null) = JSONObject()
        .put("subscription_key", "selected-sim").put("elapsed_realtime_ms", elapsed)
        .put("received_utc", "2026-11-04T15:04:00Z").put("cells", cells).apply {
            if (location != null) put("location", location)
        }

    @Test fun missingCaptureDoesNotInventServiceOrLocation() {
        val model = LiveOverviewModel.build(null, null)
        assertTrue(model.cells.isEmpty())
        assertNull(model.receivedUtc)
        assertNull(model.gps)
    }

    @Test fun latestRegisteredLteAndNrStaySeparateAndFieldsAreExplicit() {
        val lte = cell("LTE", -103)
        val nr = cell("NR", -82, "secondary")
        val neighbor = cell("LTE", -70).put("registered", false)
        val old = observation(1000, JSONArray().put(cell("LTE", -90)))
        val latest = observation(2000, JSONArray().put(lte).put(nr).put(neighbor))
        val input = JSONObject().put("observations", JSONArray().put(old).put(latest))
            .put("subscriptions", JSONArray().put(JSONObject().put("key", "selected-sim").put("network_operator", "Carrier")))
        val before = input.toString()
        val result = LiveOverviewModel.build(input, null)
        assertEquals(2, result.cells.size)
        assertEquals("LTE · Primary serving", result.cells[0].title)
        assertEquals("Carrier", result.cells[0].carrier)
        assertEquals("5230", result.cells[0].channel)
        assertEquals("3", result.cells[0].pci)
        assertEquals(-103.0, result.cells[0].values[0].value!!, 0.01)
        assertNull(result.cells[0].values[1].value)
        assertEquals("NR · Secondary serving", result.cells[1].title)
        assertEquals(-82.0, result.cells[1].values[0].value!!, 0.01)
        assertEquals("400 ms old at receipt", result.cells[0].age)
        assertEquals(before, input.toString())
    }

    @Test fun gpsIsSavedEvidenceWithReceiptAgeAndMockStatus() {
        val fix = JSONObject().put("status", "available").put("latitude_deg", 34.7).put("longitude_deg", -86.6)
            .put("horizontal_accuracy_m", 8.0).put("fix_age_ms", 1234).put("mock", true)
        val capture = JSONObject().put("observations", JSONArray().put(observation(5000, JSONArray(), fix)))
        val result = LiveOverviewModel.build(capture, null)
        assertTrue(result.gps!!.contains("Test location at capture"))
        assertTrue(result.gps!!.contains("old at receipt"))
        assertEquals("2026-11-04T15:04:00Z", result.receivedUtc)
    }

    @Test fun invalidValuesDoNotBecomeMeasuredNumbers() {
        val row = cell("LTE", -100)
        row.getJSONObject("signal").put("rsrp", JSONObject().put("value", -100).put("unit", "dB"))
        val input = JSONObject().put("observations", JSONArray().put(observation(1, JSONArray().put(row))))
        assertNull(LiveOverviewModel.build(input, null).cells.single().values.first().value)
    }
}
