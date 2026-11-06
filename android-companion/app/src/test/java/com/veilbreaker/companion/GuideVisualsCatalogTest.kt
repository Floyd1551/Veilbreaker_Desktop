package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class GuideVisualsCatalogTest {
    @Test fun everyFieldGuideHasItsOwnReadableWorkflowAndDecisionCues() {
        val ids = WirelessReferenceLibrary.entries.filter { it.category == "Guides" }.map { it.id }.toSet()
        assertEquals(10, ids.size)
        assertEquals(ids, GuideVisualsCatalog.entries.keys)
        ids.forEach { id ->
            val guide = GuideVisualsCatalog.forEntry(id)!!
            assertEquals(4, guide.stages.size)
            assertEquals(2, guide.cues.size)
            assertTrue(guide.stages.all { it.title.isNotBlank() && it.detail.isNotBlank() })
            assertTrue(guide.cues.all { it.observation.isNotBlank() && it.nextStep.isNotBlank() })
        }
        assertNull(GuideVisualsCatalog.forEntry("expanded-fspl"))
    }

    @Test fun cuesPreserveEvidenceAndSafetyDistinctions() {
        val das = GuideVisualsCatalog.forEntry("expanded-guide-das")!!
        assertTrue(das.cues.any { it.nextStep.contains("Do not assume") })
        val spectrum = GuideVisualsCatalog.forEntry("expanded-guide-spectrum")!!
        assertTrue(spectrum.cues.any { it.nextStep.contains("do not infer") })
        val cell = GuideVisualsCatalog.forEntry("expanded-guide-cell")!!
        assertTrue(cell.cues.any { it.nextStep.contains("never substitute zero") })
    }
}
