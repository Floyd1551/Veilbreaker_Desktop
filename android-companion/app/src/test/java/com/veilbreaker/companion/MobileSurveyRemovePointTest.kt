package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class MobileSurveyRemovePointTest {
    private val time = "2026-11-20T12:00:00Z"
    private fun capture(id: String) = JSONObject().put("format", "veilbreaker.android.cellular")
        .put("schema_version", 1).put("capture_id", id).put("created_utc", time)
        .put("collection", JSONObject().put("outcome", "complete"))
        .put("observations", JSONArray().put(JSONObject().put("received_utc", time)))
    private fun survey(vararg ids: String): JSONObject {
        var result = MobileSurvey.create("Survey", time)
        ids.forEach { result = MobileSurvey.addCapture(result, capture(it), time) }
        return result
    }

    @Test fun removeFirstMiddleAndLastKeepOtherPointsAndOriginalUnchanged() {
        val original = MobileSurvey.setPointNote(survey("a", "b", "c"), "b", "Visible pillar")
        val originalText = original.toString()
        for (removed in listOf("a", "b", "c")) {
            val copy = MobileSurvey.removePoint(original, removed)
            val points = copy.getJSONArray("points")
            assertEquals(2, points.length())
            val remaining = (0 until points.length()).map { points.getJSONObject(it).getJSONObject("capture").getString("capture_id") }
            assertEquals(listOf("a", "b", "c").filter { it != removed }, remaining)
            assertEquals(originalText, original.toString())
            assertEquals(copy.toString(), MobileSurvey.validate(JSONObject(copy.toString())).toString())
            if (removed != "b") assertEquals("Visible pillar", (0 until points.length()).map { points.getJSONObject(it) }
                .first { it.getJSONObject("capture").getString("capture_id") == "b" }.getString("operator_note"))
        }
    }

    @Test fun capacityIsAvailableAgainAfterRemoval() {
        var full = MobileSurvey.create("Site", time)
        repeat(20) { full = MobileSurvey.addCapture(full, capture("cap-$it"), time) }
        val reduced = MobileSurvey.removePoint(full, "cap-10")
        assertEquals(19, reduced.getJSONArray("points").length())
        assertEquals(20, MobileSurvey.addCapture(reduced, capture("replacement"), time).getJSONArray("points").length())
        assertEquals(20, full.getJSONArray("points").length())
    }

    @Test fun completedMissingInvalidAndDuplicateSurveysFailWithoutMutation() {
        val original = survey("a", "b")
        val completed = MobileSurvey.complete(original, time)
        val duplicate = JSONObject(original.toString()).apply {
            getJSONArray("points").put(JSONObject(getJSONArray("points").getJSONObject(0).toString()))
        }
        for ((candidate, target) in listOf(original to "missing", survey() to "a", completed to "a", duplicate to "a", original to "")) {
            val before = candidate.toString()
            try { MobileSurvey.removePoint(candidate, target); fail("Expected rejected removal") }
            catch (_: IllegalArgumentException) { }
            assertEquals(before, candidate.toString())
        }
    }

    @Test fun removedPointIsDetachedFromEvidenceAndRemainingPoints() {
        val a = capture("a"); val b = capture("b")
        val originalA = a.toString(); val originalB = b.toString()
        val before = MobileSurvey.addCapture(MobileSurvey.addCapture(MobileSurvey.create("Site", time), a, time), b, time)
        val after = MobileSurvey.removePoint(before, "a")
        after.getJSONArray("points").getJSONObject(0).getJSONObject("capture").put("extra", "changed")
        assertEquals(originalA, a.toString()); assertEquals(originalB, b.toString())
        assertEquals(originalB, before.getJSONArray("points").getJSONObject(1).getJSONObject("capture").toString())
    }

    @Test fun failedTransactionDoesNotMutateDurableSurveyOrOtherEvidence() {
        val latestCapture = capture("latest")
        val archivedCapture = capture("archived")
        val durable = survey("a", "b").put("operator_metadata", JSONObject().put("site", "unchanged"))
        val before = durable.toString(); val latestBefore = latestCapture.toString(); val archiveBefore = archivedCapture.toString()
        try {
            MobileSurveyTransactions.update(read = { durable }, transform = { MobileSurvey.removePoint(it, "a") },
                write = { throw IllegalStateException("Simulated storage failure") })
            fail("Expected storage failure")
        } catch (error: IllegalStateException) {
            assertEquals("Simulated storage failure", error.message)
        }
        assertEquals(before, durable.toString())
        assertEquals(latestBefore, latestCapture.toString()); assertEquals(archiveBefore, archivedCapture.toString())
        val success = MobileSurveyTransactions.update(read = { durable }, transform = { MobileSurvey.removePoint(it, "a") }, write = {})
        val reopened = MobileSurvey.validate(JSONObject(success.toString()))
        assertEquals("unchanged", reopened.getJSONObject("operator_metadata").getString("site"))
        assertEquals("b", reopened.getJSONArray("points").getJSONObject(0).getJSONObject("capture").getString("capture_id"))
    }
}
