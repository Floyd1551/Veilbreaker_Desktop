package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class CaptureWaitPolicyTest {
    @Test fun standaloneCaptureWaitsForRequestedGpsOnlyWhileFixIsPending() {
        assertTrue(CaptureWaitPolicy.waitForLocation(true, true, "unavailable", 1000, 30000))
        assertFalse(CaptureWaitPolicy.waitForLocation(true, true, "available", 1000, 30000))
        assertFalse(CaptureWaitPolicy.waitForLocation(true, true, "disabled", 1000, 30000))
        assertFalse(CaptureWaitPolicy.waitForLocation(true, true, "permission_denied", 1000, 30000))
    }
    @Test fun neverDelaysDesktopOrUnrequestedLocationAndHonorsDeadline() {
        assertFalse(CaptureWaitPolicy.waitForLocation(false, true, "unavailable", 1000, 30000))
        assertFalse(CaptureWaitPolicy.waitForLocation(true, false, "unavailable", 1000, 30000))
        assertFalse(CaptureWaitPolicy.waitForLocation(true, true, "unavailable", 30000, 30000))
    }
}
