package com.veilbreaker.companion

/** Retain one picker result until a live, recovered workspace can consume it. */
class CapturePickerMailbox<T : Any> {
    private var pending: T? = null

    @Synchronized fun offer(value: T) {
        if (pending == null) pending = value
    }

    @Synchronized fun takeIfReady(ready: Boolean): T? {
        if (!ready) return null
        return pending.also { pending = null }
    }
}
