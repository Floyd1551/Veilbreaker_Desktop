package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiSecurityCapabilitiesTest {
    @Test fun blankAndControlOnlyReportsAreUnavailable() {
        listOf(null, "", "   ", "\n\t").forEach {
            val result = WifiSecurityCapabilities.interpret(it)
            assertEquals("Unknown", result.label)
            assertNull(result.raw)
        }
    }

    @Test fun reportsExactPersonalModesAndTransition() {
        assertEquals("WPA-Personal", WifiSecurityCapabilities.interpret("[WPA-PSK-TKIP][ESS]").label)
        assertEquals("WPA2-Personal", WifiSecurityCapabilities.interpret("[WPA2-PSK-CCMP][ESS]").label)
        assertEquals("WPA3-Personal", WifiSecurityCapabilities.interpret("[RSN-SAE-CCMP][ESS]").label)
        assertEquals("WPA2/WPA3-Personal transition", WifiSecurityCapabilities.interpret("[RSN-PSK+SAE-CCMP][ESS]").label)
        assertEquals("WPA2/WPA3-Personal transition", WifiSecurityCapabilities.interpret("[WPA2-PSK-CCMP][RSN-SAE-CCMP][ESS]").label)
    }

    @Test fun reportsEnterpriseAndEnhancedOpenWithoutSuggestingSafety() {
        assertEquals("WPA2-Enterprise", WifiSecurityCapabilities.interpret("[WPA2-EAP-CCMP][ESS]").label)
        assertEquals("RSN Enterprise", WifiSecurityCapabilities.interpret("[RSN-EAP-CCMP][ESS]").label)
        assertEquals("WPA3-Enterprise 192-bit", WifiSecurityCapabilities.interpret("[RSN-EAP_SUITE_B_192-GCMP-256][MFPC][MFPR][ESS]").label)
        assertEquals("Enhanced Open (OWE)", WifiSecurityCapabilities.interpret("[RSN-OWE-CCMP][ESS]").label)
        assertEquals("OWE transition", WifiSecurityCapabilities.interpret("[OWE_TRANSITION][ESS]").label)
    }

    @Test fun openRequiresAnExplicitUnambiguousMarker() {
        assertEquals("Open", WifiSecurityCapabilities.interpret("[OPEN][ESS]").label)
        assertEquals("WEP", WifiSecurityCapabilities.interpret("[WEP][ESS]").label)
        listOf(null, "", "[ESS]", "[WPS][ESS]", "[OPEN][WEP][ESS]").forEach {
            assertEquals("Unknown", WifiSecurityCapabilities.interpret(it).label)
        }
    }

    @Test fun malformedTruncatedUnrecognizedOrAmbiguousTextNeverGetsAConfidentLabel() {
        listOf("[WPA2-PSK-CCMP", "[WPA2-PSK-CCMP]garbage", "[NOTWPA2-PSK-CCMP]", "[WPA2-PSK-CCMP][VENDOR-UNKNOWN]", "[WPA2-PSK-BOGUS]", "[WPA-PSK-TKIP][RSN-SAE-CCMP]", "[RSN-SAE-TKIP]", "[RSN-OWE-TKIP]", "[RSN-EAP_SUITE_B_192-CCMP][MFPC][MFPR]", "[WPA2-PSK-CCMP]\n[ESS]", "[ESS]".repeat(36)).forEach {
            assertEquals("Unknown", WifiSecurityCapabilities.interpret(it).label)
        }
    }

    @Test fun retainsOriginalReportAndExplainsItsLimitedProvenance() {
        val report = "[RSN-PSK+SAE-CCMP][ESS]"
        val result = WifiSecurityCapabilities.interpret(report)
        assertEquals(report, result.raw)
        assertTrue(result.note.contains("Android"))
        assertTrue(result.note.contains("advertised"))
        assertFalse(result.note.contains("safe", ignoreCase = true))
    }
}
