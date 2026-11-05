package com.veilbreaker.companion

import org.junit.Assert.assertEquals
import org.junit.Test

class SimSelectionTest {
    @Test fun keepsTheSameSubscriptionWhenTheListIsReordered() {
        assertEquals(2, SimSelection.spinnerPosition(listOf(23, 17), 17))
        assertEquals(1, SimSelection.spinnerPosition(listOf(17, 23), 17))
    }

    @Test fun clearsSelectionWhenSubscriptionWasRemoved() {
        assertEquals(0, SimSelection.spinnerPosition(listOf(23), 17))
    }

    @Test fun doesNotSelectAFirstSimWhenNothingWasSelected() {
        assertEquals(0, SimSelection.spinnerPosition(listOf(17, 23), null))
        assertEquals(0, SimSelection.spinnerPosition(emptyList(), 17))
    }
}
