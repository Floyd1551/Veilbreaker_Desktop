package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class ReferenceReaderModelTest {
    @Test fun signalReferencesClearlySeparateRangesFromTargets() {
        val wifi = ReferenceReaderModel.valueReference("wifi-rssi")!!
        assertTrue(wifi.contains("−67 dBm")); assertTrue(wifi.contains("specific"))
        val cellular = ReferenceReaderModel.valueReference("cell-power")!!
        assertTrue(cellular.contains("−140")); assertTrue(cellular.contains("not service targets"))
        assertNull(ReferenceReaderModel.valueReference("missing"))
    }
    @Test fun eachReferenceHasAnOperatorPromptAndKeepsProvenance() {
        for (entry in WirelessReferenceLibrary.entries) {
            assertTrue(ReferenceReaderModel.recordPrompt(entry).isNotBlank())
            assertTrue(ReferenceReaderModel.checks(entry).all { it.isNotBlank() })
            assertTrue(ReferenceReaderModel.checks(entry).isNotEmpty())
            assertTrue(entry.sourceName.isNotBlank())
            assertTrue(entry.reviewed.isNotBlank())
            assertTrue(entry.limitations.isNotBlank())
        }
    }

    @Test fun relatedEntriesAreBoundedDistinctAndExcludeCurrent() {
        for (entry in WirelessReferenceLibrary.entries) {
            val related = ReferenceReaderModel.related(entry)
            assertTrue(related.size <= 3)
            assertEquals(related.size, related.map { it.id }.toSet().size)
            assertTrue(related.none { it.id == entry.id })
        }
    }

    @Test fun relatedReferencesPrioritizeSharedTags() {
        val rsrp = WirelessReferenceLibrary.entries.first { it.id == "cell-power" }
        assertTrue(ReferenceReaderModel.related(rsrp).any { it.category == "Cellular" })
    }
}
