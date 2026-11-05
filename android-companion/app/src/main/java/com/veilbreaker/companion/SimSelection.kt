package com.veilbreaker.companion

/** Preserve the subscription identity, not its position in Android's active-SIM list. */
object SimSelection {
    /** Spinner position zero is the explicit "Choose a SIM" placeholder. */
    fun spinnerPosition(subscriptionIds: List<Int>, selectedSubscriptionId: Int?): Int {
        if (selectedSubscriptionId == null) return 0
        val index = subscriptionIds.indexOf(selectedSubscriptionId)
        return if (index < 0) 0 else index + 1
    }
}
