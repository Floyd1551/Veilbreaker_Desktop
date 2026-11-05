package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class NetworkTestRulesTest {
    @Test fun acceptsOnlyExplicitHttpsWithoutCredentialsOrFragments() {
        assertEquals("example.com", NetworkTestRules.target("https://example.com/file.bin?token=x").host)
        for (bad in listOf("", "http://example.com", "https://user:pass@example.com/", "https://example.com/#x",
                           "https://example.com:0/", "https://example.com:65536/", "https:///file", "https://example.com/ bad")) {
            try { NetworkTestRules.target(bad); fail("Accepted invalid URL: $bad") }
            catch (_: IllegalArgumentException) { }
        }
    }

    @Test fun throughputUsesTransferDurationAndRequiresEnoughObservedData() {
        assertEquals(8.0, NetworkTestRules.mbps(1_000_000, 1000)!!, 0.00001)
        assertNull(NetworkTestRules.mbps(1000, 1000))
        assertNull(NetworkTestRules.mbps(1_000_000, 10))
        assertNull(NetworkTestRules.mbps(0, 0))
    }
}
