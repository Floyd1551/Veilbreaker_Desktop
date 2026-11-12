package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiReferenceDetailsTest {
    @Test fun everyWifiReferenceHasSpecificUsefulOfflineSections() {
        val entries = WirelessReferenceLibrary.entries.filter { it.category == "Wi-Fi" }
        assertTrue(entries.size >= 12)
        for (entry in entries) {
            val sections = WifiReferenceDetails.sections(entry.id)
            assertTrue("${entry.id} needs interpretation and a field procedure", sections.size >= 2)
            assertTrue("${entry.id} needs substantive content", sections.sumOf { it.second.length } >= 250)
            assertTrue("${entry.id} needs a source", sections.any { it.second.contains("https://") })
        }
        assertTrue(WifiReferenceDetails.sections("unknown").isEmpty())
    }

    @Test fun keyExamplesRetainUnitsAndLimitations() {
        val overlap = WifiReferenceDetails.sections("expanded-wifi-24").joinToString { it.second }
        assertTrue(overlap.contains("2412")); assertTrue(overlap.contains("2437")); assertTrue(overlap.contains("2462"))
        val snr = WifiReferenceDetails.sections("expanded-wifi-snr").joinToString { it.second }
        assertTrue(snr.contains("−65")); assertTrue(snr.contains("−90")); assertTrue(snr.contains("25 dB"))
        assertTrue(snr.contains("not exposed"))
    }
}
