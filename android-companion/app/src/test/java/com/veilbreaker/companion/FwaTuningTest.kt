package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class FwaTuningTest {
    @Test fun rejectsInvalidAnglesMissingMetricsAndNonFiniteValues() {
        assertNull(FwaTuning.sample("Rooftop", 360.0, -100.0, null, null, null, null))
        assertNull(FwaTuning.sample("Rooftop", 10.0, null, null, null, null, null))
        assertNull(FwaTuning.sample("Rooftop", 10.0, Double.NaN, null, null, null, null))
        assertNull(FwaTuning.sample("Rooftop", 10.0, null, null, null, -1.0, null))
        assertNull(FwaTuning.sample(" ", 10.0, -100.0, null, null, null, null))
    }

    @Test fun comparesOnlyValuesPresentInBothManualTrials() {
        val baseline = FwaTuning.sample("Baseline", 10.0, -105.0, null, 2.0, 25.0, null)!!
        val later = FwaTuning.sample("East", 20.0, -95.0, -12.0, 8.0, null, 4.0)!!
        val diff = FwaTuning.difference(baseline, later)
        assertEquals(10.0, diff.rsrp!!, 0.0)
        assertEquals(6.0, diff.sinr!!, 0.0)
        assertNull(diff.rsrq)
        assertNull(diff.downlink)
        assertNull(diff.uplink)
    }
}
