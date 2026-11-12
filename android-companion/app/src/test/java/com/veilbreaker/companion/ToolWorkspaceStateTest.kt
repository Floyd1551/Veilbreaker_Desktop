package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class ToolWorkspaceStateTest {
    @Test fun selectionSurvivesSearchWhenStillVisible() {
        val state = ToolWorkspaceState()
        state.select("fresnel")
        assertEquals(1, state.indexFor(listOf("fspl", "fresnel")))
        assertEquals("fresnel", state.selected)
        assertEquals(0, state.indexFor(listOf("fspl")))
        assertEquals("fspl", state.selected)
        assertEquals(-1, state.indexFor(emptyList()))
        assertNull(state.selected)
    }

    @Test fun draftsStaySeparateAndRestoreWithoutPretendingToBeMeasurements() {
        val state = ToolWorkspaceState()
        state.saveDraft("fresnel", listOf("2400", "1", "2"))
        state.saveDraft("fspl", listOf("5800", "3"))
        assertEquals(listOf("2400", "1", "2"), state.draft("fresnel"))
        assertEquals(listOf("5800", "3"), state.draft("fspl"))
        assertEquals(emptyList<String>(), state.draft("missing"))
    }
}
