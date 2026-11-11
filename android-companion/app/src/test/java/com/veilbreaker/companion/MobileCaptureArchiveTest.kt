package com.veilbreaker.companion

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class MobileCaptureArchiveTest {
    private val time = "2026-11-11T12:00:00Z"
    private fun capture() = CaptureSerializer.envelope("Example", "Device", "16", 36, "test", emptyList(), 42, "complete", emptyList(), time)

    @Test fun archiveKeepsDistinctUnchangedCapturesAndRejectsDuplicates() {
        val original = capture(); val other = capture(); val bytes = original.toString()
        val first = MobileCaptureArchive.add(MobileCaptureArchive.empty(time), original, time)
        val second = MobileCaptureArchive.add(first, other, time)
        assertEquals(2, MobileCaptureArchive.captures(second).size)
        assertEquals(bytes, original.toString())
        assertEquals(bytes, MobileCaptureArchive.captures(second).first().toString())
        val duplicate = assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.add(second, original, time) }
        assertEquals("This capture is already archived.", duplicate.message)
    }

    @Test fun removeChangesOnlyTheArchiveCopyAndRejectsUnknownId() {
        val one = capture(); val two = capture()
        val archive = MobileCaptureArchive.add(MobileCaptureArchive.add(MobileCaptureArchive.empty(time), one, time), two, time)
        val removed = MobileCaptureArchive.remove(archive, one.getString("capture_id"))
        assertEquals(2, MobileCaptureArchive.captures(archive).size)
        assertEquals(two.getString("capture_id"), MobileCaptureArchive.captures(removed).single().getString("capture_id"))
        assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.remove(archive, "missing") }
    }

    @Test fun archiveRejectsMalformedAndForeignSurvey() {
        assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.captures(JSONObject()) }
        assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.captures(MobileSurvey.create("Other", time)) }
    }

    @Test fun fullArchiveRejectsAnotherCaptureWithoutChangingExistingCopies() {
        var archive = MobileCaptureArchive.empty(time)
        repeat(20) { archive = MobileCaptureArchive.add(archive, capture(), time) }
        val before = archive.toString()
        val full = assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.add(archive, capture(), time) }
        assertTrue(full.message.orEmpty().contains("20 captures"))
        assertEquals(before, archive.toString())
        assertEquals(20, MobileCaptureArchive.captures(archive).size)
    }

    @Test fun archivedCaptureCanBeCopiedIntoAnOpenSurveyWithoutChangingArchive() {
        val captured = capture(); val id = captured.getString("capture_id")
        val archive = MobileCaptureArchive.add(MobileCaptureArchive.empty(time), captured, time)
        val survey = MobileSurvey.create("Field site", time)
        val beforeArchive = archive.toString(); val beforeSurvey = survey.toString()
        val updated = MobileCaptureArchive.addToSurvey(archive, survey, id, time)
        assertEquals(beforeArchive, archive.toString()); assertEquals(beforeSurvey, survey.toString())
        assertEquals(id, updated.getJSONArray("points").getJSONObject(0).getJSONObject("capture").getString("capture_id"))
        assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.addToSurvey(archive, updated, id, time) }
        assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.addToSurvey(archive, survey, "missing", time) }
        assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.addToSurvey(archive, MobileSurvey.complete(survey, time), id, time) }
        var full = survey
        repeat(20) { full = MobileSurvey.addCapture(full, capture(), time) }
        val fullBefore = full.toString()
        assertThrows(IllegalArgumentException::class.java) { MobileCaptureArchive.addToSurvey(archive, full, id, time) }
        assertEquals(fullBefore, full.toString()); assertEquals(beforeArchive, archive.toString())
    }
}
