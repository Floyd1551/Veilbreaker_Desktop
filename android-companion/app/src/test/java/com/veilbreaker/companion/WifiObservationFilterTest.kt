package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiObservationFilterTest {
    private val rows = listOf(
        WifiObservationFilter.Row("Office", "00:11:22:33:44:55", 2412, -75, 10),
        WifiObservationFilter.Row("Guest", "00:11:22:33:44:66", 5180, -48, null),
        WifiObservationFilter.Row(null, null, 5955, -127, 20),
        WifiObservationFilter.Row("Office", "00:11:22:33:44:77", 2437, -62, 90)
    )

    @Test fun searchMatchesNameAndBssidWithoutInventingHiddenName() {
        assertEquals(2, WifiObservationFilter.select(rows, "office", WifiObservationFilter.Band.ALL, WifiObservationFilter.Order.SIGNAL).size)
        assertEquals("Guest", WifiObservationFilter.select(rows, "44:66", WifiObservationFilter.Band.ALL, WifiObservationFilter.Order.SIGNAL).single().ssid)
        assertEquals(0, WifiObservationFilter.select(rows, "hidden", WifiObservationFilter.Band.ALL, WifiObservationFilter.Order.SIGNAL).size)
    }

    @Test fun bandsExcludeUnknownAndSixGhzSpecialCaseIsRecognized() {
        assertEquals(2, WifiObservationFilter.select(rows, "", WifiObservationFilter.Band.GHZ_24, WifiObservationFilter.Order.SIGNAL).size)
        assertEquals(1, WifiObservationFilter.select(rows, "", WifiObservationFilter.Band.GHZ_5, WifiObservationFilter.Order.SIGNAL).size)
        val special = WifiObservationFilter.Row(null, null, 5935, -80, null)
        assertEquals(2, WifiObservationFilter.select(rows + special, "", WifiObservationFilter.Band.GHZ_6, WifiObservationFilter.Order.SIGNAL).size)
    }

    @Test fun sortingPlacesUnavailableSignalAndAgeLast() {
        assertEquals(listOf(-48, -62, -75, -127), WifiObservationFilter.select(rows, "", WifiObservationFilter.Band.ALL, WifiObservationFilter.Order.SIGNAL).map { it.rssiDbm })
        assertEquals(listOf(10L, 20L, 90L, null), WifiObservationFilter.select(rows, "", WifiObservationFilter.Band.ALL, WifiObservationFilter.Order.AGE).map { it.ageSeconds })
        assertEquals(listOf(2412, 2437, 5180, 5955), WifiObservationFilter.select(rows, "", WifiObservationFilter.Band.ALL, WifiObservationFilter.Order.FREQUENCY).map { it.frequencyMhz })
    }
}
