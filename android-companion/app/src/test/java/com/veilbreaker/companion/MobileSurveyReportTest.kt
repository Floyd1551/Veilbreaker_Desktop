package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class MobileSurveyReportTest {
    @Test fun reportSeparatesLocationAndCellObservationTimes() {
        val value = capture("one", "complete", -86)
        val old = value.getJSONArray("observations").getJSONObject(0)
        old.put("location", JSONObject().put("status", "available").put("source", "phone").put("provider", "gps")
            .put("latitude_deg", 34.7).put("longitude_deg", -86.6).put("horizontal_accuracy_m", 10)
            .put("fix_age_ms", 500).put("fix_utc", "2026-11-05T11:59:59Z").put("mock", false))
        val next = JSONObject(old.toString()); next.remove("location")
        next.put("elapsed_realtime_ms", 200).put("received_utc", "2026-11-05T12:00:05Z")
        value.getJSONArray("observations").put(next)
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Site", stamp), value, stamp)
        val before = survey.toString()
        val report = MobileSurveyReport.build(survey, null)
        val html = MobileSurveyReport.html(report)
        assertTrue(report.points.single().location.contains("Location observation received 2026-11-05T12:00:00Z"))
        assertTrue(html.contains("Fix time 2026-11-05T11:59:59Z"))
        assertTrue(html.contains("observation assembled 2026-11-05T12:00:05Z"))
        assertEquals(before, survey.toString())
    }
    private val stamp = "2026-11-05T12:00:00Z"
    private fun capture(id: String, outcome: String, power: Int): JSONObject {
        val cell = JSONObject().put("radio", "LTE").put("registered", true).put("connection_status", "primary")
            .put("identity", JSONObject().put("pci", 17)).put("signal", JSONObject().put("rsrp", JSONObject().put("value", power).put("unit", "dBm")))
        val obs = JSONObject().put("subscription_key", "sim-1").put("elapsed_realtime_ms", 100)
            .put("received_utc", stamp).put("cells", JSONArray().put(cell))
        return JSONObject().put("format", "veilbreaker.android.cellular").put("schema_version", 1)
            .put("capture_id", id).put("created_utc", stamp).put("collection", JSONObject().put("outcome", outcome))
            .put("observations", JSONArray().put(obs))
    }

    @Test fun buildsSurveySummaryAndPointDetailsWithoutChangingSource() {
        var survey = MobileSurvey.create("Warehouse", stamp)
        survey = MobileSurvey.addCapture(survey, capture("one", "complete", -86), stamp)
        survey = MobileSurvey.addCapture(survey, capture("two", "partial", -103), stamp)
        survey = MobileSurvey.setPointNote(survey, "two", "Concrete pillar")
        val original = survey.toString()
        val report = MobileSurveyReport.build(survey, null)
        assertEquals(2, report.points.size)
        assertEquals(1, report.completeCount)
        assertEquals(1, report.partialCount)
        assertEquals("Concrete pillar", report.points[1].operatorNote)
        assertTrue(report.points[0].servingCells.single().metrics.contains("RSRP: -86 dBm"))
        assertEquals(original, survey.toString())
    }

    @Test fun portableHtmlEscapesNamesAndNotesAndIdentifiesMissingValues() {
        var survey = MobileSurvey.addCapture(MobileSurvey.create("Site <north>", stamp), capture("one", "partial", -86), stamp)
        survey = MobileSurvey.setPointNote(survey, "one", "<script>alert(1)</script>")
        val html = MobileSurveyReport.html(MobileSurveyReport.build(survey, null))
        assertTrue(html.contains("Site &lt;north&gt;"))
        assertTrue(html.contains("&lt;script&gt;"))
        assertFalse(html.contains("<script>"))
        assertTrue(html.contains("No valid reported location"))
        assertTrue(html.contains("Original captures"))
        assertTrue(html.contains("not live"))
    }

    @Test fun includesOnlyReportedReceiverCoordinatesWhenPresent() {
        val value = capture("one", "complete", -86)
        value.getJSONArray("observations").getJSONObject(0).put("location", JSONObject()
            .put("status", "available").put("source", "phone").put("provider", "gps")
            .put("latitude_deg", 34.7).put("longitude_deg", -86.6).put("horizontal_accuracy_m", 10)
            .put("fix_age_ms", 500).put("mock", false))
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Site", stamp), value, stamp)
        val report = MobileSurveyReport.build(survey, null)
        assertEquals(34.7, report.locations[1]!!.latitude, 0.0)
        assertTrue(MobileSurveyReport.html(report).contains("34.7, -86.6"))
        assertTrue(report.points[0].location.contains("Fix time not exposed"))
    }

    @Test fun unknownMockStatusIsVisibleInDashboardAndExport() {
        val value = capture("one", "complete", -86)
        val location = JSONObject().put("status", "available").put("source", "phone").put("provider", "gps")
            .put("latitude_deg", 34.7).put("longitude_deg", -86.6).put("horizontal_accuracy_m", 10)
            .put("fix_age_ms", 500)
        value.getJSONArray("observations").getJSONObject(0).put("location", location)
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Site", stamp), value, stamp)
        val original = survey.toString()
        val report = MobileSurveyReport.build(survey, null)
        assertTrue(report.points[0].location.contains("mock status unknown"))
        assertTrue(MobileSurveyReport.html(report).contains("mock status unknown"))
        assertEquals(original, survey.toString())
    }

    @Test fun emptyAndFailedSurveysDoNotLookComplete() {
        val empty = MobileSurvey.create("Empty", stamp)
        val emptyReport = MobileSurveyReport.build(empty, null)
        assertEquals(0, emptyReport.points.size)
        assertTrue(MobileSurveyReport.html(emptyReport).contains("No captures"))
        val failed = MobileSurvey.addCapture(empty, capture("failure", "failed", -86), stamp)
        val report = MobileSurveyReport.build(failed, null)
        assertEquals(0, report.completeCount)
        assertEquals(0, report.partialCount)
        assertEquals("failed", report.points[0].outcome)
    }
}
