package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class GnssReferenceTest {
    @Test fun locationAccuracyReferenceIsSearchableAndPreservesProvenance() {
        val entry = WirelessReferenceLibrary.search("RF", "gps accuracy").first { it.id == "rf-location-quality" }
        val text = ReferenceReaderModel.expanded(entry).joinToString(" ") { it.second }
        assertTrue(text.contains("68%"))
        assertTrue(text.contains("horizontal"))
        assertTrue(text.contains("manual", ignoreCase = true))
        assertTrue(text.contains("elapsed", ignoreCase = true))
        assertTrue(entry.sourceUrl.startsWith("https://developer.android.com/"))
        assertNotNull(ReferenceVisualData.table(entry.id))
    }

    @Test fun satelliteReferenceExplainsWhatTheCountsAndCn0DoNotProve() {
        val entry = WirelessReferenceLibrary.search(null, "gnss satellites").first { it.id == "rf-gnss-satellites" }
        val text = ReferenceReaderModel.expanded(entry).joinToString(" ") { it.second }
        assertTrue(text.contains("used", ignoreCase = true))
        assertTrue(text.contains("dB-Hz"))
        assertTrue(text.contains("RSSI"))
        assertTrue(text.contains("not", ignoreCase = true))
        assertNotNull(ReferenceVisualData.table(entry.id))
    }
}
