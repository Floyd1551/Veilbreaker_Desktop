package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiDisplayTest {
    @Test fun signalBarUsesFixedLabeledRangeAndKeepsUnknownUnknown() {
        assertNull(WifiDisplay.barPercent(null))
        assertNull(WifiDisplay.barPercent(-127))
        assertNull(WifiDisplay.barPercent(1))
        assertEquals(0, WifiDisplay.barPercent(-120))
        assertEquals(50, WifiDisplay.barPercent(-75))
        assertEquals(100, WifiDisplay.barPercent(-30))
        assertEquals(100, WifiDisplay.barPercent(-5))
    }

    @Test fun frequenciesAndAgesAreNotConflated() {
        assertEquals("Channel 36 (derived) · 5180 MHz", WifiDisplay.channelText(5180))
        assertEquals("Frequency unavailable", WifiDisplay.channelText(null))
        assertEquals("Channel unknown · 2413 MHz", WifiDisplay.channelText(2413))
        assertEquals("Age unavailable", WifiDisplay.ageText(null))
        assertEquals("15 s old at view", WifiDisplay.ageText(15))
    }
}
