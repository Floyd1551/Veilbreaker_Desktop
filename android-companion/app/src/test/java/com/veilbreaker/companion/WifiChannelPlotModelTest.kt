package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiChannelPlotModelTest {
    @Test fun aggregatesOnlyValidObservationsByBandAndFrequency() {
        val points = WifiChannelPlotModel.aggregate(listOf(
            WifiChannelPlotModel.Sample(2412, -70, 5), WifiChannelPlotModel.Sample(2412, -48, 30),
            WifiChannelPlotModel.Sample(5180, -65, null), WifiChannelPlotModel.Sample(5935, -83, 1),
            WifiChannelPlotModel.Sample(2412, -127, 1), WifiChannelPlotModel.Sample(0, -65, 1)
        ))
        assertEquals(3, points.size)
        val point = points.first { it.frequencyMhz == 2412 }
        assertEquals(WifiChannelPlotModel.Band.GHZ_24, point.band)
        assertEquals(-48, point.strongestDbm)
        assertEquals(2, point.observationCount)
        assertTrue(points.any { it.band == WifiChannelPlotModel.Band.GHZ_5 })
        assertTrue(points.any { it.band == WifiChannelPlotModel.Band.GHZ_6 && it.frequencyMhz == 5935 })
    }

    @Test fun recordsAgeRangeAndUnknownWithoutPretendingFreshness() {
        val point = WifiChannelPlotModel.aggregate(listOf(
            WifiChannelPlotModel.Sample(5955, -52, 15), WifiChannelPlotModel.Sample(5955, -67, null),
            WifiChannelPlotModel.Sample(5955, -60, 40)
        )).single()
        assertEquals(15L, point.youngestSeconds)
        assertEquals(40L, point.oldestSeconds)
        assertEquals(1, point.ageUnavailableCount)
    }

    @Test fun emptyOrInvalidDataDoesNotInventPoints() {
        assertTrue(WifiChannelPlotModel.aggregate(emptyList()).isEmpty())
        assertTrue(WifiChannelPlotModel.aggregate(listOf(
            WifiChannelPlotModel.Sample(900, -80, 1), WifiChannelPlotModel.Sample(2412, 1, 1),
            WifiChannelPlotModel.Sample(5180, -127, null)
        )).isEmpty())
    }
}
