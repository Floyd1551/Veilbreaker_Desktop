package com.veilbreaker.companion

import java.net.URI

/** Pure validation and arithmetic for the opt-in transport-bound test. */
object NetworkTestRules {
    fun target(input: String): URI {
        val value = input.trim()
        require(value.length in 1..2048) { "Enter an HTTPS URL (up to 2048 characters)." }
        val uri = try { URI(value) } catch (_: Exception) { throw IllegalArgumentException("Enter a valid HTTPS URL.") }
        require(uri.scheme.equals("https", true) && !uri.host.isNullOrBlank() && uri.userInfo == null &&
            uri.fragment == null && (uri.port == -1 || uri.port in 1..65535)) {
            "Enter an HTTPS URL without credentials or a fragment."
        }
        return uri
    }

    /** Mbps from received payload bits and transfer time; very short tests are not representative. */
    fun mbps(bytes: Long, elapsedMs: Long): Double? {
        if (bytes < 100_000 || elapsedMs < 250) return null
        return bytes.toDouble() * 8.0 / elapsedMs / 1000.0
    }
}
