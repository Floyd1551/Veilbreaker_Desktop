package com.veilbreaker.companion

/** Navigation within the Activity never changes its USB foreground lifecycle. */
enum class WorkspacePage { LIVE, DIAGNOSE, SURVEY, REPORTS }

object WorkspaceNavigation {
    fun restore(index: Int): WorkspacePage = WorkspacePage.entries.getOrElse(index) { WorkspacePage.LIVE }
    fun canOpenExternal(connected: Boolean, pending: Boolean): Boolean = !connected && !pending
}
