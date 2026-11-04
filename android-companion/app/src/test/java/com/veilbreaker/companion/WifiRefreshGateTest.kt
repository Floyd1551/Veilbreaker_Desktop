package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiRefreshGateTest {
    @Test fun callbackBurstsScheduleOneRefreshAndStopCancelsIt() {
        val gate = WifiRefreshGate()
        assertFalse(gate.request())
        gate.start()
        assertTrue(gate.request())
        repeat(50) { assertFalse(gate.request()) }
        assertTrue(gate.consume())
        assertFalse(gate.consume())
        assertTrue(gate.request())
        gate.stop()
        assertFalse(gate.consume())
        assertFalse(gate.request())
        gate.start()
        assertTrue(gate.request())
        assertTrue(gate.consume())
    }

    @Test fun fullRefreshCancelsPendingCallbackWithoutDisablingFutureUpdates() {
        val gate = WifiRefreshGate()
        gate.start()
        assertTrue(gate.request())
        gate.cancel()
        assertFalse(gate.consume())
        assertTrue(gate.request())
        assertTrue(gate.consume())
    }
}
