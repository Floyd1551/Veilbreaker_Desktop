package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class MobileSurveyTest {
    private fun capture(id: String = "cap-1") = JSONObject().put("format", "veilbreaker.android.cellular")
        .put("schema_version", 1).put("capture_id", id).put("created_utc", "2026-11-04T12:00:00Z")
        .put("collection", JSONObject().put("outcome", "complete"))
        .put("observations", JSONArray().put(JSONObject().put("received_utc", "2026-11-04T12:00:00Z")
            .put("location", JSONObject().put("status", "unavailable"))))

    @Test fun attachesIndependentCaptureAndKeepsUnknownLocation() {
        val original = capture()
        val survey = MobileSurvey.create("Warehouse", "2026-11-04T12:00:00Z")
        val next = MobileSurvey.addCapture(survey, original, "2026-11-04T12:01:00Z")
        original.put("capture_id", "mutated")
        assertEquals(0, survey.getJSONArray("points").length())
        val stored = next.getJSONArray("points").getJSONObject(0).getJSONObject("capture")
        assertEquals("cap-1", stored.getString("capture_id"))
        val location = stored.getJSONArray("observations").getJSONObject(0).getJSONObject("location")
        assertEquals("unavailable", location.getString("status"))
        assertFalse(location.has("latitude_deg"))
        assertEquals("veilbreaker.mobile.survey", next.getString("format"))
    }

    @Test fun duplicateCapturesAndCompletedSurveyAreRejected() {
        val t = "2026-11-04T12:00:00Z"
        var survey = MobileSurvey.addCapture(MobileSurvey.create("Site", t), capture(), t)
        try { MobileSurvey.addCapture(survey, capture(), t); fail("duplicate") } catch (_: IllegalArgumentException) { }
        survey = MobileSurvey.complete(survey, t)
        try { MobileSurvey.addCapture(survey, capture("cap-2"), t); fail("completed") } catch (_: IllegalArgumentException) { }
        survey = MobileSurvey.reopen(survey)
        assertEquals(2, MobileSurvey.addCapture(survey, capture("cap-2"), t).getJSONArray("points").length())
    }

    @Test fun newlyCollectedSurveyPointRetainsPartialButRejectsFailedOrCancelled() {
        val t = "2026-11-04T12:00:00Z"
        val survey = MobileSurvey.create("Site", t)
        val partial = capture("partial")
        partial.getJSONObject("collection").put("outcome", "partial")
        val updated = MobileSurvey.addNewCapture(survey, partial, t)
        assertEquals("partial", updated.getJSONArray("points").getJSONObject(0)
            .getJSONObject("capture").getJSONObject("collection").getString("outcome"))
        try { MobileSurvey.addNewCapture(updated, partial, t); fail("duplicate") } catch (_: IllegalArgumentException) { }
        try { MobileSurvey.addNewCapture(MobileSurvey.complete(survey, t), capture("another"), t); fail("completed") } catch (_: IllegalArgumentException) { }
        for (outcome in listOf("cancelled", "failed")) {
            val invalid = capture(outcome)
            invalid.getJSONObject("collection").put("outcome", outcome)
            try { MobileSurvey.addNewCapture(survey, invalid, t); fail(outcome) } catch (_: IllegalArgumentException) { }
        }
        assertEquals(0, survey.getJSONArray("points").length())
    }

    @Test fun operatorNoteIsStoredOnPointWithoutChangingCapturedEvidence() {
        val t = "2026-11-04T12:00:00Z"
        val original = capture()
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Site", t), original, t)
        val before = original.toString()
        val updated = MobileSurvey.setPointNote(survey, "cap-1", "Concrete pillar north of measurement")
        assertEquals(before, original.toString())
        val point = updated.getJSONArray("points").getJSONObject(0)
        assertEquals("Concrete pillar north of measurement", point.getString("operator_note"))
        assertEquals(before, point.getJSONObject("capture").toString())
        assertFalse(survey.getJSONArray("points").getJSONObject(0).has("operator_note"))
        assertEquals(updated.toString(), MobileSurvey.validate(JSONObject(updated.toString())).toString())
        val cleared = MobileSurvey.setPointNote(updated, "cap-1", " ")
        assertFalse(cleared.getJSONArray("points").getJSONObject(0).has("operator_note"))
    }

    @Test fun operatorNoteRejectsMissingPointInvalidTextAndCompletedSurvey() {
        val t = "2026-11-04T12:00:00Z"
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Site", t), capture(), t)
        for (note in listOf("x".repeat(501), "invalid\u0000control")) {
            try { MobileSurvey.setPointNote(survey, "cap-1", note); fail("invalid note") } catch (_: IllegalArgumentException) { }
        }
        try { MobileSurvey.setPointNote(survey, "missing", "note"); fail("missing point") } catch (_: IllegalArgumentException) { }
        try { MobileSurvey.setPointNote(MobileSurvey.complete(survey, t), "cap-1", "note"); fail("completed") } catch (_: IllegalArgumentException) { }
        assertFalse(survey.getJSONArray("points").getJSONObject(0).has("operator_note"))
    }

    @Test fun validatesNamesBoundsAndCaptureShape() {
        val t = "2026-11-04T12:00:00Z"
        for (name in listOf("", " ", "x".repeat(81))) {
            try { MobileSurvey.create(name, t); fail("name") } catch (_: IllegalArgumentException) { }
        }
        var survey = MobileSurvey.create("Site", t)
        try { MobileSurvey.addCapture(survey, JSONObject(), t); fail("capture") } catch (_: IllegalArgumentException) { }
        repeat(20) { survey = MobileSurvey.addCapture(survey, capture("cap-$it"), t) }
        try { MobileSurvey.addCapture(survey, capture("extra"), t); fail("limit") } catch (_: IllegalArgumentException) { }
    }

    @Test fun pointSummaryUsesOnlyReportedServingValues() {
        val sample = capture()
        val cell = JSONObject().put("radio", "LTE").put("registered", true)
            .put("signal", JSONObject().put("rsrp", JSONObject().put("value", -96).put("unit", "dBm")))
        sample.getJSONArray("observations").getJSONObject(0).put("cells", JSONArray().put(cell))
        val result = MobileSurvey.signalSummary(sample)
        assertTrue(result.contains("RSRP -96 dBm"))
        assertTrue(result.contains("SINR not exposed"))
        assertFalse(result.contains("0 dB"))
    }

    @Test fun surveyMapUsesLastValidFixPerCaptureWithoutInventingCoordinates() {
        val t = "2026-11-04T12:00:00Z"
        val withLocation = capture("one")
        val observations = withLocation.getJSONArray("observations")
        observations.put(JSONObject().put("received_utc", t).put("location", JSONObject()
            .put("status", "available").put("latitude_deg", 34.7).put("longitude_deg", -86.6)
            .put("horizontal_accuracy_m", 12).put("fix_age_ms", 1500).put("mock", true)))
        var survey = MobileSurvey.addCapture(MobileSurvey.create("Site", t), withLocation, t)
        survey = MobileSurvey.addCapture(survey, capture("two"), t)
        val fixes = GpsSpatialModel.surveyLocations(survey)
        assertEquals(1, fixes.size)
        assertEquals(1, fixes[0].pointNumber)
        assertEquals("one", fixes[0].captureId)
        assertEquals(34.7, fixes[0].fix.latitude, 0.00001)
        assertEquals(1500L, fixes[0].fix.ageAtReceiptMs)
        assertTrue(fixes[0].fix.mock)
    }
}
