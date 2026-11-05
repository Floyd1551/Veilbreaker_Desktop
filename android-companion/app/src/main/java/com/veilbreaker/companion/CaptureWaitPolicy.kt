package com.veilbreaker.companion

/** Bounded foreground GPS wait; a USB session retains its existing sampling cadence. */
object CaptureWaitPolicy {
    fun waitForLocation(standalone: Boolean, requested: Boolean, status: String?, now: Long, deadline: Long): Boolean =
        standalone && requested && status == "unavailable" && now < deadline
}
