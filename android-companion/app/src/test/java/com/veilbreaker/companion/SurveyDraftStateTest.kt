package com.veilbreaker.companion

import org.junit.Assert.assertEquals
import org.junit.Test

class SurveyDraftStateTest {
    @Test fun restoresOnlyDraftsForPointsStillInTheOpenedSurvey() {
        val drafts = linkedMapOf("capture-1" to "Concrete pillar", "capture-2" to "", "other" to "Wrong survey")
        assertEquals(mapOf("capture-1" to "Concrete pillar", "capture-2" to ""),
            SurveyDraftState.retain(drafts, setOf("capture-1", "capture-2")))
    }

    @Test fun rejectsOversizedDraftsAndLimitsRestoredEntries() {
        val drafts = linkedMapOf("too-long" to "x".repeat(501))
        repeat(25) { drafts["capture-$it"] = "Note $it" }
        val validIds = drafts.keys.toSet()
        val retained = SurveyDraftState.retain(drafts, validIds)
        assertEquals(20, retained.size)
        assertEquals(false, retained.containsKey("too-long"))
    }

    @Test fun removesCommittedDraftsAndRetainsUnwrittenEditsAfterReopening() {
        val drafts = mapOf("saved" to " Concrete pillar ", "cleared" to "  ", "failed" to "Draft remains")
        val saved = mapOf("saved" to "Concrete pillar", "cleared" to null, "failed" to "Old note")
        assertEquals(mapOf("failed" to "Draft remains"), SurveyDraftState.reconcile(drafts, saved))
    }
}
