package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class LiveGpsSummaryTest {
    @Test fun satelliteDetailsKeepUseAndConstellationsDistinct() {
        val observations = listOf(
            LiveGpsSummary.Satellite("GPS", 4, true, 32.2f, 45f, 90f),
            LiveGpsSummary.Satellite("Galileo", 12, false, 18f, 20f, 180f))
        val summary = LiveGpsSummary.satellites(observations)
        assertTrue(summary.contains("2 reported · 1 used in last fix"))
        assertTrue(summary.contains("GPS 4 · used"))
        assertTrue(summary.contains("Galileo 12 · not used"))
        assertTrue(summary.contains("32.2 dB-Hz"))
    }

    @Test fun missingOrInvalidValuesAreNotInvented() {
        assertEquals("No satellite report received yet.", LiveGpsSummary.satellites(null))
        assertEquals("0 reported · 0 used in last fix", LiveGpsSummary.satellites(emptyList()))
        val row = LiveGpsSummary.Satellite("Unknown", 0, false, Float.NaN, Float.NaN, Float.NaN)
        val result = LiveGpsSummary.satellites(listOf(row))
        assertFalse(result.contains("NaN"))
        assertTrue(result.contains("signal not exposed"))
    }
}
