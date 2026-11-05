package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WorkspaceNavigationTest {
    @Test fun restoreRejectsInvalidPageValues() {
        assertEquals(WorkspacePage.LIVE, WorkspaceNavigation.restore(-1))
        assertEquals(WorkspacePage.LIVE, WorkspaceNavigation.restore(99))
        assertEquals(WorkspacePage.SURVEY, WorkspaceNavigation.restore(2))
        assertEquals(WorkspacePage.REPORTS, WorkspaceNavigation.restore(3))
        assertEquals(WorkspacePage.TOOLS, WorkspaceNavigation.restore(4))
    }

    @Test fun externalActivitiesAreBlockedWhileCapturingOrConnected() {
        assertTrue(WorkspaceNavigation.canOpenExternal(false, false))
        assertFalse(WorkspaceNavigation.canOpenExternal(true, false))
        assertFalse(WorkspaceNavigation.canOpenExternal(false, true))
        assertFalse(WorkspaceNavigation.canOpenExternal(true, true))
    }
}
