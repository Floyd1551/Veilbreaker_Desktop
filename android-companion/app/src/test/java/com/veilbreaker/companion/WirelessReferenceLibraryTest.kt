package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WirelessReferenceLibraryTest {
    @Test fun emptyQueryShowsAllReferences() {
        assertEquals(WirelessReferenceLibrary.entries, WirelessReferenceLibrary.search(null, "  "))
    }
    @Test fun searchMatchesTagsAndIgnoresCase() {
        val entries = WirelessReferenceLibrary.search(null, "  SINR  ")
        assertTrue(entries.any { it.category == "Cellular" })
        assertTrue(entries.all { it.searchableText.contains("sinr") || ReferenceReaderModel.expanded(it).any { section -> section.second.lowercase().contains("sinr") } })
        assertTrue(WirelessReferenceLibrary.search(null, "bSsId").isNotEmpty())
    }
    @Test fun searchRequiresAllTermsAndSelectedCategory() {
        val found = WirelessReferenceLibrary.search("Wi-Fi", "signal rssi")
        assertTrue(found.isNotEmpty())
        assertTrue(found.all { it.category == "Wi-Fi" })
        assertTrue(WirelessReferenceLibrary.search("Cellular", "bssid").isEmpty())
        assertTrue(WirelessReferenceLibrary.search("Unknown", "").isEmpty())
    }
    @Test fun everyEntryIncludesSourceDateAndLimits() {
        assertTrue(WirelessReferenceLibrary.entries.size >= 8)
        assertEquals(WirelessReferenceLibrary.entries.size, WirelessReferenceLibrary.entries.map { it.id }.toSet().size)
        assertTrue(WirelessReferenceLibrary.entries.all { it.sourceUrl.startsWith("https://") && it.sourceName.isNotBlank() && it.reviewed.matches(Regex("\\d{4}-\\d{2}-\\d{2}")) && it.limitations.isNotBlank() })
    }
}
