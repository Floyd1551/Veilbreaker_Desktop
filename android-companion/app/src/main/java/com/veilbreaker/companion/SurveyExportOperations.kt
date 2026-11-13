package com.veilbreaker.companion

/** In-process write status survives Activity recreation without retaining an Activity. */
class SurveyExportOperations {
    data class State(val running: Boolean, val error: String?)
    private val states = LinkedHashMap<String, State>()

    @Synchronized fun begin(token: String): Boolean {
        val previous = states[token]
        if (previous != null && (previous.running || previous.error == null)) return false
        while (states.size >= 100) {
            val old = states.entries.firstOrNull { !it.value.running } ?: break
            states.remove(old.key)
        }
        states[token] = State(true, null)
        return true
    }

    @Synchronized fun finish(token: String, error: String?) {
        if (states[token]?.running == true) states[token] = State(false, error)
    }

    @Synchronized fun status(token: String): State? = states[token]
}
