package com.veilbreaker.companion

/** One approval attempt per explicit phone arming. The displayed code is not a credential. */
class UsbPairing(private val now: () -> Long, private val token: String) {
    private var request: String? = null
    private var deadline = 0L
    private var approved = false
    private var consumed = false
    fun begin(id: String, code: String) {
        require(request == null && id.matches(Regex("[a-f0-9]{32}")) && code.matches(Regex("[0-9]{6}")))
        request = id; deadline = now() + 60000
    }
    private fun check(id: String) { require(request == id && now() <= deadline && !consumed) }
    fun approve(id: String) { check(id); approved = true }
    fun deny() { consumed = true }
    fun poll(id: String): String? {
        check(id)
        if (!approved) return null
        consumed = true
        return token
    }
}
