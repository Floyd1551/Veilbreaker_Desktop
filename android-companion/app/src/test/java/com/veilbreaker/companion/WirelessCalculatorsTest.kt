package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WirelessCalculatorsTest {
    @Test fun wifiChannelConversionsUseSelectedBandAndSpecialCases() {
        assertEquals(2412, WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_24, 1))
        assertEquals(2484, WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_24, 14))
        assertEquals(5180, WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_5, 36))
        assertEquals(5955, WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_6, 1))
        assertEquals(5935, WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_6, 2))
        assertEquals(2, WirelessCalculators.mhzToChannel(WirelessCalculators.Band.GHZ_6, 5935))
        assertEquals(233, WirelessCalculators.mhzToChannel(WirelessCalculators.Band.GHZ_6, 7115))
    }
    @Test fun wifiConversionRejectsInvalidBandAndOffGridFrequency() {
        assertNull(WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_24, 0))
        assertNull(WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_24, 15))
        assertNull(WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_5, 200))
        assertNull(WirelessCalculators.mhzToChannel(WirelessCalculators.Band.GHZ_24, 2413))
        assertNull(WirelessCalculators.mhzToChannel(WirelessCalculators.Band.GHZ_5, 2412))
        assertNull(WirelessCalculators.mhzToChannel(WirelessCalculators.Band.GHZ_6, 5960))
    }
    @Test fun powerConversionAndRoundTrip() {
        assertEquals(1.0, WirelessCalculators.dbmToMw(0.0)!!, 1e-12)
        assertEquals(100.0, WirelessCalculators.dbmToMw(20.0)!!, 1e-10)
        assertEquals(0.0000001, WirelessCalculators.dbmToMw(-70.0)!!, 1e-16)
        assertEquals(-70.0, WirelessCalculators.mwToDbm(0.0000001)!!, 1e-10)
    }
    @Test fun powerConversionRejectsNonFiniteAndNonPositiveOrOverflow() {
        assertNull(WirelessCalculators.mwToDbm(0.0))
        assertNull(WirelessCalculators.mwToDbm(-1.0))
        assertNull(WirelessCalculators.mwToDbm(Double.POSITIVE_INFINITY))
        assertNull(WirelessCalculators.dbmToMw(Double.NaN))
        assertNull(WirelessCalculators.dbmToMw(4000.0))
        assertNull(WirelessCalculators.dbmToMw(-4000.0))
    }
}
