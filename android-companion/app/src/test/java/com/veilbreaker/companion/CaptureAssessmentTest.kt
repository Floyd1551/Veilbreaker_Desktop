package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class CaptureAssessmentTest {
    @Test fun missingRequestedLocationMakesCellularCapturePartialWithoutDiscardingCells() {
        val result = CaptureAssessment.assess(true, 4, true, null, true, "unavailable")
        assertEquals("partial", result.outcome)
        assertTrue(result.notes.any { it.contains("location", ignoreCase = true) })
    }
    @Test fun requestedLocationOnlyWithoutFixIsPartial() {
        assertEquals("partial", CaptureAssessment.assess(false, 0, true, null, true, "disabled").outcome)
        assertEquals("complete", CaptureAssessment.assess(false, 0, true, null, true, "available").outcome)
    }
    @Test fun unrequestedLocationDoesNotDowngradeCellularAndRealErrorsDo() {
        assertEquals("complete", CaptureAssessment.assess(true, 1, true, null, false, null).outcome)
        assertEquals("partial", CaptureAssessment.assess(true, 0, true, null, false, null).outcome)
        assertEquals("partial", CaptureAssessment.assess(true, 2, true, "timeout", false, null).outcome)
        assertEquals("partial", CaptureAssessment.assess(true, 257, true, null, false, null).outcome)
        assertEquals("partial", CaptureAssessment.assess(true, 0, false, null, false, null).outcome)
    }
}
