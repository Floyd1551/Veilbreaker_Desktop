package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiFieldCountersReferenceTest {
    @Test fun retryCounterReferenceIsSearchableAndExplainsScope() {
        val entry = WirelessReferenceLibrary.search("Wi-Fi", "retry counters").first { it.id == "wifi-retry-counters" }
        val details = WifiReferenceDetails.sections(entry.id).joinToString(" ") { it.second }
        assertTrue(details.contains("one or more"))
        assertTrue(details.contains("success", ignoreCase = true))
        assertTrue(details.contains("denominator", ignoreCase = true))
        assertTrue(details.contains("direction", ignoreCase = true))
        assertTrue(entry.sourceUrl.startsWith("https://www.cisco.com/"))
        val table = ReferenceVisualData.table(entry.id)!!
        assertTrue(table.rows.any { it.first.contains("Failed", ignoreCase = true) })
        assertTrue(table.note.contains("definition", ignoreCase = true))
    }

    @Test fun utilizationReferenceSeparatesMeasuredBusyFromNearbyScans() {
        val entry = WirelessReferenceLibrary.search("Wi-Fi", "channel utilization").first { it.id == "wifi-busy-time" }
        val details = WifiReferenceDetails.sections(entry.id).joinToString(" ") { it.second }
        assertTrue(details.contains("scan", ignoreCase = true))
        assertTrue(details.contains("interval", ignoreCase = true))
        assertTrue(details.contains("not", ignoreCase = true))
        assertTrue(details.contains("http"))
        val table = ReferenceVisualData.table(entry.id)!!
        assertTrue(table.note.contains("not", ignoreCase = true))
        assertTrue(table.rows.any { it.first.contains("scan", ignoreCase = true) })
    }
}
