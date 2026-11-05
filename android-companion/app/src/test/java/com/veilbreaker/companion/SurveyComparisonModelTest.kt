package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class SurveyComparisonModelTest {
    private val t = "2026-11-05T12:00:00Z"
    private val plan = JSONObject().put("ranges", JSONArray())

    private fun sample(id: String, outcome: String, cells: JSONArray = JSONArray(), location: JSONObject? = null): JSONObject {
        val observation = JSONObject().put("subscription_key", "selected-sim").put("elapsed_realtime_ms", 100)
            .put("received_utc", t).put("cells", cells)
        if (location != null) observation.put("location", location)
        return JSONObject().put("format", "veilbreaker.android.cellular").put("schema_version", 1)
            .put("capture_id", id).put("created_utc", t).put("collection", JSONObject().put("outcome", outcome))
            .put("observations", JSONArray().put(observation))
    }
    private fun lte(rsrp: Int, registered: Boolean = true) = JSONObject().put("radio", "LTE")
        .put("registered", registered).put("connection_status", if (registered) "primary" else "none")
        .put("identity", JSONObject().put("pci", 17).put("earfcn", 5230))
        .put("signal", JSONObject().put("rsrp", JSONObject().put("value", rsrp).put("unit", "dBm")))

    @Test fun showsEachPointsOwnServingMeasurementsAndKeepsOriginalCapture() {
        var survey = MobileSurvey.create("Field", t)
        survey = MobileSurvey.addCapture(survey, sample("p1", "complete", JSONArray().put(lte(-86))), t)
        survey = MobileSurvey.addCapture(survey, sample("p2", "partial", JSONArray().put(lte(-103))), t)
        val before = survey.toString()
        val rows = SurveyComparisonModel.build(survey, plan)
        assertEquals(before, survey.toString())
        assertEquals(2, rows.size)
        assertTrue(rows[0].servingCells.single().metrics.any { it == "RSRP: -86 dBm" })
        assertTrue(rows[1].servingCells.single().metrics.any { it == "RSRP: -103 dBm" })
        assertEquals("partial", rows[1].outcome)
        assertTrue(rows[0].location.contains("No valid"))
    }

    @Test fun reportsMissingOrMockLocationAndExcludesNeighborFromServingSummary() {
        val location = JSONObject().put("status", "available").put("source", "phone").put("provider", "gps")
            .put("latitude_deg", 34.7).put("longitude_deg", -86.6).put("horizontal_accuracy_m", 12)
            .put("fix_age_ms", 5000).put("mock", true)
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Field", t), sample("p1", "complete", JSONArray().put(lte(-55, false)), location), t)
        val row = SurveyComparisonModel.build(survey, plan).single()
        assertTrue(row.servingCells.isEmpty())
        assertTrue(row.location.contains("mock"))
        assertTrue(row.location.contains("5000 ms old at receipt"))
        assertEquals("p1", row.captureId)
    }

    @Test fun capsDisplayedServingCellsAndReportsOmissions() {
        val cells = JSONArray()
        repeat(6) { cells.put(lte(-90)) }
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Field", t), sample("p1", "complete", cells), t)
        val row = SurveyComparisonModel.build(survey, plan).single()
        assertEquals(4, row.servingCells.size)
        assertEquals(2, row.omittedServing)
    }

    @Test fun pointReviewKeepsOperatorObservationSeparateFromMeasuredValues() {
        var survey = MobileSurvey.addCapture(MobileSurvey.create("Field", t), sample("p1", "complete", JSONArray().put(lte(-86))), t)
        assertNull(SurveyComparisonModel.build(survey, plan).single().operatorNote)
        survey = MobileSurvey.setPointNote(survey, "p1", "Concrete pillar near antenna")
        val row = SurveyComparisonModel.build(survey, plan).single()
        assertEquals("Concrete pillar near antenna", row.operatorNote)
        assertTrue(row.servingCells.single().metrics.any { it == "RSRP: -86 dBm" })
    }
}
