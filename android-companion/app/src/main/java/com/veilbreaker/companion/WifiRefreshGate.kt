package com.veilbreaker.companion

/** Coalesce foreground callback bursts into one connected-network redraw. */
class WifiRefreshGate {
    private var active = false
    private var pending = false

    fun start() { active = true }
    fun stop() { active = false; pending = false }
    fun cancel() { pending = false }
    fun request(): Boolean {
        if (!active || pending) return false
        pending = true
        return true
    }
    fun consume(): Boolean {
        val redraw = active && pending
        pending = false
        return redraw
    }
}
