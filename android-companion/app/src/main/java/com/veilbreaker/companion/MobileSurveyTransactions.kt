package com.veilbreaker.companion

/** One process-wide monitor, shared by every survey store and activity instance. */
internal object MobileSurveyTransactions {
    private val monitor = Any()

    fun <T> locked(action: () -> T): T = synchronized(monitor) { action() }

    /** Keep read, validation/transformation and durable write in a single critical section. */
    fun <T> update(read: () -> T, transform: (T) -> T, write: (T) -> Unit): T = locked {
        val updated = transform(read())
        write(updated)
        updated
    }
}
