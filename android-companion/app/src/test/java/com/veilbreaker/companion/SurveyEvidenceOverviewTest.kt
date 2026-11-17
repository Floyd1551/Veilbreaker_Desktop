package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class SurveyEvidenceOverviewTest {
    private val stamp = "2026-11-05T12:00:00Z"

    private fun capture(id: String, registered: Boolean, location: JSONObject?): JSONObject {
        val cell = JSONObject().put("radio", "LTE").put("registered", registered)
            .put("connection_status", if (registered) "primary" else "none")
            .put("identity", JSONObject().put("pci", 17)).put("signal", JSONObject())
        val observation = JSONObject().put("subscription_key", "sim-1").put("elapsed_realtime_ms", 100)
            .put("received_utc", stamp).put("cells", JSONArray().put(cell))
        if (location != null) observation.put("location", location)
        return JSONObject().put("format", "veilbreaker.android.cellular").put("schema_version", 1)
            .put("capture_id", id).put("created_utc", stamp)
            .put("collection", JSONObject().put("outcome", "complete"))
            .put("observations", JSONArray().put(observation))
    }

    private fun location(mock: Boolean?, timed: Boolean): JSONObject {
        val row = JSONObject().put("status", "available").put("source", "phone")
            .put("latitude_deg", 34.7).put("longitude_deg", -86.6).put("horizontal_accuracy_m", 12)
        if (mock != null) row.put("mock", mock)
        if (timed) row.put("fix_utc", "2026-11-05T11:59:59Z").put("fix_age_ms", 1000)
        return row
    }

    @Test fun overviewCountsAvailableEvidenceWithoutInterpretingSignalHealth() {
        var survey = MobileSurvey.create("Survey", stamp)
        survey = MobileSurvey.addCapture(survey, capture("one", true, location(false, true)), stamp)
        survey = MobileSurvey.addCapture(survey, capture("two", false, null), stamp)
        survey = MobileSurvey.addCapture(survey, capture("three", true, location(true, false)), stamp)
        survey = MobileSurvey.addCapture(survey, capture("four", true, location(null, false)), stamp)
        val before = survey.toString()
        val report = MobileSurveyReport.build(survey, null)
        val overview = report.overview
        assertEquals(4, overview.captures)
        assertEquals(3, overview.withLocation)
        assertEquals(1, overview.withoutLocation)
        assertEquals(1, overview.mockMarked)
        assertEquals(1, overview.mockUnknown)
        assertEquals(1, overview.withLocationTimes)
        assertEquals(3, overview.withRegisteredCellShown)
        assertEquals(0, overview.incompleteCellReviews)
        assertEquals(before, survey.toString())
        val html = MobileSurveyReport.html(report)
        assertTrue(html.contains("Reported receiver location: 3 of 4 captures"))
        assertTrue(html.contains("No valid location in reviewed observations: 1 of 4 captures"))
        assertTrue(html.contains("Marked mock: 1 of 3 reported locations"))
        assertTrue(html.contains("not a signal health score"))
    }

    @Test fun emptySurveyHasZeroCountsAndNoInventedEvidence() {
        val report = MobileSurveyReport.build(MobileSurvey.create("Empty", stamp), null)
        assertEquals(0, report.overview.captures)
        assertEquals(0, report.overview.withLocation)
        assertEquals(0, report.overview.withRegisteredCellShown)
        assertTrue(MobileSurveyReport.html(report).contains("Reported receiver location: 0 of 0 captures"))
    }

    @Test fun truncatedCellReviewIsCountedAndDisclosed() {
        val value = capture("many", true, null)
        val cells = value.getJSONArray("observations").getJSONObject(0).getJSONArray("cells")
        repeat(256) { cells.put(JSONObject().put("radio", "GSM").put("registered", false)) }
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Long capture", stamp), value, stamp)
        val report = MobileSurveyReport.build(survey, null)
        assertEquals(1, report.overview.incompleteCellReviews)
        val html = MobileSurveyReport.html(report)
        assertTrue(html.contains("Cell review limited or unavailable: 1 of 1 captures"))
        assertTrue(html.contains("Some cell entries or observations may be skipped or unavailable"))
    }
}
