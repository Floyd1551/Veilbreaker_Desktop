package com.veilbreaker.companion

import java.nio.file.Files
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class SurveyReportRestorationTest {
    private val stamp = "2026-11-13T12:00:00Z"

    private fun capture(id: String, outcome: String, rsrp: Int): JSONObject {
        val signal = JSONObject().put("rsrp", JSONObject().put("value", rsrp).put("unit", "dBm"))
        val cell = JSONObject().put("radio", "LTE").put("registered", true)
            .put("connection_status", "primary").put("identity", JSONObject().put("pci", 17)).put("signal", signal)
        val observation = JSONObject().put("subscription_key", "sim-1").put("elapsed_realtime_ms", 100)
            .put("received_utc", stamp).put("cells", JSONArray().put(cell))
        return JSONObject().put("format", "veilbreaker.android.cellular").put("schema_version", 1)
            .put("capture_id", id).put("created_utc", stamp)
            .put("collection", JSONObject().put("outcome", outcome))
            .put("observations", JSONArray().put(observation))
    }

    @Test fun onlyRebuildsWhenTheReportWasOpen() {
        val saved = MobileSurvey.create("Saved survey", "2026-11-13T12:00:00Z")
        assertNull(SurveyReportRestoration.restore(false, saved, null))
        val report = SurveyReportRestoration.restore(true, saved, null)!!
        assertEquals("Saved survey", report.name)
        assertTrue(report.points.isEmpty())
    }

    @Test fun rebuildUsesValidatedSavedSurveyWithoutChangingPriorExport() {
        val original = MobileSurvey.create("Before edit", "2026-11-13T12:00:00Z")
        val stagedExport = MobileSurveyReport.html(MobileSurveyReport.build(original, null))
        val saved = JSONObject(original.toString()).put("name", "After edit")
        val savedBytes = saved.toString()
        val rebuilt = SurveyReportRestoration.restore(true, saved, null)!!
        assertEquals("After edit", rebuilt.name)
        assertTrue(stagedExport.contains("Before edit"))
        assertFalse(stagedExport.contains("After edit"))
        assertEquals(savedBytes, saved.toString())
    }

    @Test fun invalidSavedSurveyDoesNotProduceAReport() {
        assertThrows(IllegalArgumentException::class.java) {
            SurveyReportRestoration.restore(true, JSONObject(), null)
        }
    }

    @Test fun recreationRebuildsSavedMeasurementsWithoutChangingTheStagedReport() {
        var original = MobileSurvey.create("Floor survey", stamp)
        original = MobileSurvey.addCapture(original, capture("first", "complete", -86), stamp)
        original = MobileSurvey.setPointNote(original, "first", "North doorway")
        val beforeHtml = MobileSurveyReport.html(MobileSurveyReport.build(original, null))
            .toByteArray(Charsets.UTF_8)
        val directory = Files.createTempDirectory("restored-report").toFile()
        try {
            val staged = PendingSurveyExportStore(directory).stage("report", beforeHtml)
            var later = MobileSurvey.addCapture(original, capture("second", "partial", -103), stamp)
            later = MobileSurvey.setPointNote(later, "second", "Concrete pillar")
            val serialized = later.toString()
            val loadedAfterRecreation = JSONObject(serialized)

            val rebuilt = SurveyReportRestoration.restore(true, loadedAfterRecreation, null)!!
            assertEquals(2, rebuilt.points.size)
            assertEquals(1, rebuilt.completeCount)
            assertEquals(1, rebuilt.partialCount)
            assertEquals("North doorway", rebuilt.points[0].operatorNote)
            assertEquals("Concrete pillar", rebuilt.points[1].operatorNote)
            assertTrue(rebuilt.points[0].servingCells.single().metrics.contains("RSRP: -86 dBm"))
            assertTrue(rebuilt.points[1].servingCells.single().metrics.contains("RSRP: -103 dBm"))
            assertEquals(serialized, loadedAfterRecreation.toString())
            assertArrayEquals(beforeHtml, PendingSurveyExportStore(directory).read(staged))
            assertFalse(String(beforeHtml, Charsets.UTF_8).contains("Concrete pillar"))
        } finally { directory.deleteRecursively() }
    }

    @Test fun noRequestedViewDoesNotDependOnInvalidOrMissingSurveyFields() {
        assertNull(SurveyReportRestoration.restore(false, JSONObject(), null))
    }

    @Test fun damagedSavedCaptureIsNotPresentedAsAValidReport() {
        val survey = MobileSurvey.addCapture(MobileSurvey.create("Damaged", stamp),
            capture("first", "complete", -86), stamp)
        survey.getJSONArray("points").getJSONObject(0).getJSONObject("capture").remove("observations")
        val original = survey.toString()
        assertThrows(IllegalArgumentException::class.java) {
            SurveyReportRestoration.restore(true, survey, null)
        }
        assertEquals(original, survey.toString())
    }
}
