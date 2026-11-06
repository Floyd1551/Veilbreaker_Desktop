package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class ExpandedFieldReferencesTest {
    @Test fun expandedLibraryHasDistinctSourcedReferencesAndGuides() {
        val all = ExpandedFieldReferences.entries
        val guides = all.filter { it.category == "Guides" }
        assertTrue(all.count { it.category != "Guides" } >= 40)
        assertEquals(10, guides.size)
        assertEquals(all.size, all.map { it.id }.toSet().size)
        assertTrue(all.all { it.sourceUrl.startsWith("https://") && it.reviewed.matches(Regex("\\d{4}-\\d{2}-\\d{2}")) && it.limitations.isNotBlank() })
        assertTrue(guides.all { it.fieldUse.lines().count { line -> line.isNotBlank() } >= 5 })
        assertTrue(guides.all { it.fieldUse.contains("DECISION POINT") && it.fieldUse.contains("FIELD EXAMPLE") && it.fieldUse.contains("DATA QUALITY") && it.fieldUse.contains("NEXT ACTION") })
        assertTrue(guides.all { it.fieldUse.length >= 1000 })
    }

    @Test fun searchCanFindExamplesByKeywordsAndCategory() {
        assertTrue(WirelessReferenceLibrary.search("Guides", "das").any { it.title.contains("DAS") })
        assertTrue(WirelessReferenceLibrary.search("Networking", "mtu").any { it.title.contains("MTU") })
        assertTrue(WirelessReferenceLibrary.search("RF", "fresnel").isNotEmpty())
        assertTrue(WirelessReferenceLibrary.search("Fiber & Power", "poe").isNotEmpty())
    }
}
