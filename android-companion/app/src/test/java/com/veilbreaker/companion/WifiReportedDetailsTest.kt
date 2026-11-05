package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiReportedDetailsTest {
    @Test fun widthsAndCentersAreReportedWithoutInferringMissingSegments() {
        assertEquals("20 MHz", WifiReportedDetails.width(0, 5210, 5290))
        assertEquals("80 MHz · center 5210 MHz", WifiReportedDetails.width(2, 5210, 0))
        assertEquals("80+80 MHz · centers 5210 MHz / 5530 MHz", WifiReportedDetails.width(4, 5210, 5530))
        assertEquals("80+80 MHz · first center 5210 MHz · second center not exposed", WifiReportedDetails.width(4, 5210, 0))
        assertEquals("320 MHz · center not exposed", WifiReportedDetails.width(5, 0, 0))
        assertEquals("Not exposed", WifiReportedDetails.width(-1, 5210, 0))
        assertEquals("Not exposed", WifiReportedDetails.width(null, 5210, 0))
    }

    @Test fun securityStringsAreBoundedSanitizedAndNeverInferOpen() {
        assertNull(WifiReportedDetails.security(null))
        assertNull(WifiReportedDetails.security(" \n "))
        assertEquals("[WPA2-PSK-CCMP] [ESS]", WifiReportedDetails.security("[WPA2-PSK-CCMP]\n[ESS]"))
        assertEquals("[ESS]", WifiReportedDetails.security("[ESS]"))
        assertTrue(WifiReportedDetails.security("X".repeat(300))!!.length <= 180)
    }
}
