package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class CaptureReportContentTest {
    private fun capture(location: JSONObject? = null): JSONObject {
        val obs = JSONObject().put("subscription_key", "selected-sim").put("observation_id", "sample-1")
            .put("received_utc", "2026-11-04T10:00:00Z").put("elapsed_realtime_ms", 10000)
            .put("cells", JSONArray().put(JSONObject().put("radio", "LTE").put("registered", true)
                .put("connection_status", "primary").put("age_ms", 100)
                .put("identity", JSONObject().put("cell_id", "123").put("mcc", "311").put("mnc", "480"))
                .put("signal", JSONObject().put("rsrp", JSONObject().put("value", -96).put("unit", "dBm")))))
        if (location != null) obs.put("location", location)
        return JSONObject().put("format", "veilbreaker.android.cellular").put("schema_version", 1)
            .put("capture_id", "test-id").put("created_utc", "2026-11-04T10:00:00Z")
            .put("collection", JSONObject().put("mode", "snapshot").put("outcome", "partial"))
            .put("subscriptions", JSONArray()).put("observations", JSONArray().put(obs))
    }

    @Test fun reportUsesCapturedValuesAndLabelsMissingGps() {
        val input = capture(); val original = input.toString()
        val report = CaptureReportContent.build(input, JSONObject().put("ranges", JSONArray()))
        assertTrue(report.contains("-96 dBm")); assertTrue(report.contains("partial"))
        assertTrue(report.contains("Location not recorded")); assertTrue(report.contains("not a continuous measurement"))
        assertEquals(original, input.toString())
    }

    @Test fun locationIsShownOnlyWhenActuallyAvailable() {
        val loc = JSONObject().put("status", "available").put("latitude_deg", 34.7).put("longitude_deg", -86.6)
            .put("horizontal_accuracy_m", 8.0).put("fix_age_ms", 1000).put("provider", "gps").put("mock", true)
        val report = CaptureReportContent.build(capture(loc), JSONObject().put("ranges", JSONArray()))
        assertTrue(report.contains("34.700000")); assertTrue(report.contains("-86.600000")); assertTrue(report.contains("Test location"))
        val missing = CaptureReportContent.build(capture(JSONObject().put("status", "unavailable")), JSONObject().put("ranges", JSONArray()))
        assertTrue(missing.contains("Location unavailable at capture")); assertFalse(missing.contains("0.000000"))
    }
}
