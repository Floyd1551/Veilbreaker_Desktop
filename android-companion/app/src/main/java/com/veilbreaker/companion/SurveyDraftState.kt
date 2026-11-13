package com.veilbreaker.companion

/** UI drafts are transient operator text, never captured evidence or saved survey data. */
object SurveyDraftState {
    fun retain(drafts: Map<String, String>, captureIds: Set<String>): Map<String, String> = drafts
        .asSequence()
        .filter { (id, note) -> id in captureIds && note.length <= 500 }
        .take(MobileSurvey.MAX_POINTS)
        .associate { it.key to it.value }

    /** Remove only drafts already reflected in the reloaded, successfully persisted survey. */
    fun reconcile(drafts: Map<String, String>, savedNotes: Map<String, String?>): Map<String, String> =
        retain(drafts, savedNotes.keys).filter { (id, draft) ->
            val value = draft.trim()
            value.any { it.isISOControl() && it != '\n' } || value != (savedNotes[id] ?: "")
        }
}
