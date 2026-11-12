package com.veilbreaker.companion

/** Transient operator drafts, independent of captured evidence and calculated results. */
internal class ToolWorkspaceState {
    var selected: String? = null
        private set
    private val drafts = mutableMapOf<String, List<String>>()

    fun select(id: String) { selected = id }
    fun indexFor(ids: List<String>): Int {
        if (ids.isEmpty()) { selected = null; return -1 }
        val index = ids.indexOf(selected).takeIf { it >= 0 } ?: 0
        selected = ids[index]
        return index
    }
    fun saveDraft(id: String, values: List<String>) { drafts[id] = values.toList() }
    fun draft(id: String): List<String> = drafts[id].orEmpty()
}
