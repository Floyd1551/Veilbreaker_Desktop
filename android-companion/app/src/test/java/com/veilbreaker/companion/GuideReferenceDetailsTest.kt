package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class GuideReferenceDetailsTest {
    @Test fun everyGuideHasDistinctActionableWorksheet() {
        val guides = WirelessReferenceLibrary.entries.filter { it.category == "Guides" }
        assertEquals(10, guides.size)
        val sections = guides.map { GuideReferenceDetails.sections(it.id) }
        assertTrue(sections.all { it.isNotEmpty() && it.all { (title, body) -> title.isNotBlank() && body.length > 150 } })
        assertEquals(guides.size, sections.map { it.first().second }.toSet().size)
        assertTrue(GuideReferenceDetails.sections("not-a-guide").isEmpty())
    }
}
