package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class LiveCellFreshnessTest {
    @Test fun elapsedResponseAgeIsSeparateFromModemSampleAge() {
        assertEquals("Response received 0 s ago. Modem sample age is shown at receipt; the response may be cached.",
            LiveCellFreshness.describe(10000, 10999))
        assertEquals("Response received 12 s ago. Modem sample age is shown at receipt; the response may be cached.",
            LiveCellFreshness.describe(10000, 22000))
    }

    @Test fun rejectsMissingOrReversedMonotonicTime() {
        assertNull(LiveCellFreshness.describe(null, 10000))
        assertNull(LiveCellFreshness.describe(10000, 9999))
        assertNull(LiveCellFreshness.describe(-1, 10000))
    }
}
