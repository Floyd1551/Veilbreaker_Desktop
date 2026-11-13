package com.veilbreaker.companion

/** Coordinates survey writes registered before a workspace starts its background worker. */
class SurveyPendingWrites {
    private val monitor = java.lang.Object()
    private val pending = mutableMapOf<String, Int>()

    fun register(surveyId: String): AutoCloseable {
        synchronized(monitor) { pending[surveyId] = (pending[surveyId] ?: 0) + 1 }
        var closed = false
        return AutoCloseable {
            synchronized(monitor) {
                if (!closed) {
                    closed = true
                    val count = pending.getValue(surveyId)
                    if (count == 1) pending.remove(surveyId) else pending[surveyId] = count - 1
                    monitor.notifyAll()
                }
            }
        }
    }

    fun await(surveyId: String) {
        synchronized(monitor) {
            while ((pending[surveyId] ?: 0) > 0) monitor.wait()
        }
    }

    fun awaitAll() {
        synchronized(monitor) {
            while (pending.isNotEmpty()) monitor.wait()
        }
    }
}
