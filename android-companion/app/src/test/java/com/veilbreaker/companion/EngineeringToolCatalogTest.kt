package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class EngineeringToolCatalogTest {
    private fun calc(id: String, vararg values: Double): Double? =
        EngineeringToolCatalog.tools.single { it.id == id }.evaluate(values.toList())

    @Test fun powerAndWifiConvertersAreSearchableAndValidateTheGrid() {
        assertTrue(EngineeringToolCatalog.search("dBm mW").any { it.id == "dbmtomw" })
        assertTrue(EngineeringToolCatalog.search("wifi channel").any { it.id == "wifi24" })
        assertEquals(100.0, calc("dbmtomw", 20.0)!!, 0.000001)
        assertEquals(20.0, calc("mwtodbm", 100.0)!!, 0.000001)
        assertEquals(2484.0, calc("wifi24", 14.0)!!, 0.0)
        assertEquals(5935.0, calc("wifi6", 2.0)!!, 0.0)
        assertNull(calc("wifi5", 36.5))
        assertNull(calc("mwtodbm", 0.0))
    }

    @Test fun catalogHasSearchableUniqueTools() {
        assertTrue(EngineeringToolCatalog.tools.size >= 28)
        assertEquals(EngineeringToolCatalog.tools.size, EngineeringToolCatalog.tools.map { it.id }.toSet().size)
        assertTrue(EngineeringToolCatalog.search("Fresnel").any { it.id == "fresnel" })
        assertTrue(EngineeringToolCatalog.search("mss").any { it.id == "mss4" })
    }

    @Test fun propagationUsesPhysicalUnitsAndLimits() {
        assertEquals(100.05, calc("fspl", 2400.0, 1.0)!!, 0.02)
        assertEquals(0.12491, calc("wavelength", 2400.0)!!, 0.00001)
        assertEquals(5.59, calc("fresnel", 2400.0, 0.5, 0.5)!!, 0.02)
        assertNull(calc("fspl", 0.0, 1.0))
        assertNull(calc("wavelength", Double.NaN))
        assertNull(calc("fresnel", 2400.0, -1.0, 1.0))
        assertEquals(19.55, calc("horizon", 30.0, 1.0)!!, 0.02)
        assertNull(calc("horizon", 1_000_000.0, 1.0))
        assertEquals(266.85, calc("doppler", 800.0, 100.0)!!, 0.02)
        assertNull(calc("doppler", 800.0, 3_000_000.0))
    }

    @Test fun radioBudgetsAndMismatchUsePowerNotAmplitude() {
        assertEquals(28.0, calc("eirp", 20.0, 10.0, 2.0)!!, 1e-9)
        assertEquals(-62.0, calc("link", 20.0, 10.0, 2.0, 100.0, 10.0)!!, 1e-9)
        assertEquals(-104.0, calc("thermal", 10.0, 0.0)!!, 0.05)
        assertEquals(0.512, calc("mismatch", 2.0)!!, 0.002)
        assertEquals(11.111, calc("reflected", 2.0)!!, 0.002)
        assertNull(calc("mismatch", 0.5))
        assertNull(calc("thermal", 0.0, 5.0))
    }

    @Test fun networkingAndPhysicalBudgetsUseCorrectConversions() {
        assertEquals(1460.0, calc("mss4", 1500.0)!!, 0.0)
        assertEquals(1440.0, calc("mss6", 1500.0)!!, 0.0)
        assertEquals(1_250_000.0, calc("bdp", 100.0, 100.0)!!, 0.001)
        assertEquals(0.12, calc("serialization", 1500.0, 100.0)!!, 0.00001)
        assertEquals(7.0, calc("fiberloss", 10.0, 0.4, 3.0)!!, 1e-9)
        assertEquals(4.0, calc("runtime", 100.0, 20.0, 80.0)!!, 1e-9)
        assertNull(calc("runtime", 100.0, 0.0, 80.0))
        assertNull(calc("mss4", 40.0))
    }

    @Test fun nrRasterUsesThreePiecewiseRangesAndRejectsOffGridNumbers() {
        assertEquals(2999.995, calc("nrchannel", 599999.0)!!, 0.000001)
        assertEquals(3000.0, calc("nrchannel", 600000.0)!!, 0.000001)
        assertEquals(24250.08, calc("nrchannel", 2016667.0)!!, 0.000001)
        assertEquals(99999.96, calc("nrchannel", 3279165.0)!!, 0.000001)
        assertNull(calc("nrchannel", 123.5))
        assertNull(calc("nrchannel", 3279166.0))
        assertEquals(30.0, calc("nrscs", 1.0)!!, 0.0)
        assertNull(calc("nrscs", 1.5))
    }

    @Test fun remainingCalculatorsMatchKnownEngineeringExamples() {
        assertEquals(0.031228, calc("quarterwave", 2400.0)!!, 0.00001)
        assertEquals(25.85, calc("erp", 28.0)!!, 0.00001)
        assertEquals(20.0, calc("snr", -80.0, -100.0)!!, 0.0)
        assertEquals(20.0, calc("fade", -80.0, -100.0)!!, 0.0)
        assertEquals(0.05886, calc("bulge", 1.0, 1.0, 4.0 / 3.0)!!, 0.0001)
        assertEquals(9.0, calc("coax", 150.0, 6.0)!!, 0.0)
        assertEquals(6.0, calc("lossstack", 1.0, 2.0, 3.0)!!, 0.0)
        assertEquals(9.5424, calc("returnloss", 2.0)!!, 0.001)
        assertNull(calc("returnloss", 1.0))
        assertEquals(3.0103, calc("polarization", 45.0)!!, 0.001)
        assertEquals(0.07958, calc("density", 30.0, 1.0)!!, 0.0001)
        assertEquals(60.0, calc("tdd", 6.0, 10.0)!!, 0.0)
        assertEquals(100.0, calc("tcpwindow", 1_250_000.0, 100.0)!!, 0.0)
        assertEquals(0.5, calc("propdelay", 100.0, 2.0 / 3.0)!!, 0.001)
        assertEquals(17.0, calc("fiberbudget", -3.0, -20.0)!!, 0.0)
        assertEquals(15.0, calc("poe", 60.0, 45.0)!!, 0.0)
    }

    @Test fun rejectsMissingAndNonFiniteInputs() {
        assertNull(calc("eirp", 20.0, 10.0))
        assertNull(calc("eirp", 20.0, 10.0, Double.POSITIVE_INFINITY))
        assertNull(calc("polarization", 90.0))
    }
}
