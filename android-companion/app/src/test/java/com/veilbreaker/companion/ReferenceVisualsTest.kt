package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class ReferenceVisualsTest {
    @Test fun formattedPowerTablesPreserveKnownReferenceValues() {
        val dbm = ReferenceVisualData.table("expanded-dbm-table")!!
        assertEquals("1", dbm.rows.single { it.first == "0" }.second)
        assertEquals("100", dbm.rows.single { it.first == "20" }.second)
        assertEquals("1,000 (1 W)", dbm.rows.single { it.first == "30" }.second)
        val ratios = ReferenceVisualData.table("expanded-db-ratio-table")!!
        assertEquals("+3.01", ratios.rows.single { it.first == "2×" }.second)
        assertTrue(ratios.note.contains("Power ratios"))
    }

    @Test fun cidrAddressCountsAndMasksAreAccurateAndNotCalledUsableHosts() {
        val table = ReferenceVisualData.table("expanded-cidr-table")!!
        assertEquals("255.255.255.0 · 256", table.rows.single { it.first == "/24" }.second)
        assertEquals("255.255.255.252 · 4", table.rows.single { it.first == "/30" }.second)
        assertEquals("255.255.255.254 · 2", table.rows.single { it.first == "/31" }.second)
        assertTrue(table.note.contains("usable host counts"))
    }

    @Test fun pscUsesPublishedChannelsAndCorrectFrequencyRaster() {
        val table = ReferenceVisualData.table("expanded-wifi-6")!!
        assertEquals(listOf("5", "21", "37", "53", "69", "85", "101", "117", "133", "149", "165", "181", "197", "213", "229"), table.rows.map { it.first })
        assertEquals(listOf("5975", "6055", "6135", "6215", "6295", "6375", "6455", "6535", "6615", "6695", "6775", "6855", "6935", "7015", "7095"), table.rows.map { it.second })
        assertTrue(table.note.contains("does not imply regional authorization"))
    }

    @Test fun noiseAndCellularTablesRetainUnitsAndLimitations() {
        val noise = ReferenceVisualData.table("rf-noise")!!
        assertEquals("−101.0", noise.rows.single { it.first == "20 MHz" }.second)
        assertTrue(noise.note.contains("excludes receiver noise figure"))
        val cell = ReferenceVisualData.table("cell-quality")!!
        assertEquals("dBm", cell.rows.single { it.first == "LTE RSRP" }.second)
        assertEquals("dB", cell.rows.single { it.first == "NR SS-SINR" }.second)
        assertNull(ReferenceVisualData.table("not-a-reference"))
    }
}
