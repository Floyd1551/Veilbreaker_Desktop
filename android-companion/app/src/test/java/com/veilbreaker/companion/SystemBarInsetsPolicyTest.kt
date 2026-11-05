package com.veilbreaker.companion

import org.junit.Assert.assertEquals
import org.junit.Test

class SystemBarInsetsPolicyTest {
    @Test fun android15InsetsKeepAllExistingPaddingIncludingLandscapeEdges() {
        val base = SystemBarInsetsPolicy.Edges(14, 12, 14, 10)
        val bars = SystemBarInsetsPolicy.Edges(42, 28, 0, 24)
        val expected = SystemBarInsetsPolicy.Edges(56, 40, 14, 34)
        assertEquals(expected, SystemBarInsetsPolicy.padding(base, bars, 35))
        // Reapplying an inset always starts with the original padding.
        assertEquals(expected, SystemBarInsetsPolicy.padding(base, bars, 35))
    }

    @Test fun earlierAndroidPreservesSystemManagedLayout() {
        val base = SystemBarInsetsPolicy.Edges(5, 6, 7, 8)
        val bars = SystemBarInsetsPolicy.Edges(20, 30, 40, 50)
        assertEquals(base, SystemBarInsetsPolicy.padding(base, bars, 34))
        assertEquals(base, SystemBarInsetsPolicy.padding(base, bars, 29))
    }
}
