package com.veilbreaker.companion

/** Navigation within the Activity never changes its USB foreground lifecycle. */
enum class WorkspacePage { LIVE, DIAGNOSE, SURVEY, REPORTS, TOOLS }

object WorkspaceNavigation {
    fun restore(index: Int): WorkspacePage = WorkspacePage.entries.getOrElse(index) { WorkspacePage.LIVE }
    fun canOpenExternal(connected: Boolean, pending: Boolean): Boolean = !connected && !pending
    fun bottomColumns(widthDp: Int, fontScale: Float): Int =
        if (widthDp / fontScale.coerceAtLeast(1f) < 260f) 3 else 5
}
