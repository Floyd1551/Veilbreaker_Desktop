package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class CellRfReferenceDetailsTest {
    @Test fun allCellularAndRfReferencesHaveTopicSpecificSections() {
        val entries = WirelessReferenceLibrary.entries.filter { it.category == "Cellular" || it.category == "RF" }
        assertTrue(entries.size >= 20)
        for (entry in entries) {
            val sections = CellRfReferenceDetails.sections(entry.id)
            assertTrue("Missing detail for ${entry.id}", sections.size >= 2)
            assertTrue("Empty detail for ${entry.id}", sections.all { it.first.isNotBlank() && it.second.length >= 80 })
        }
        assertTrue(CellRfReferenceDetails.sections("unknown").isEmpty())
    }

    @Test fun calculationsAndApiRangesKeepTheirQualifications() {
        val freeSpace = CellRfReferenceDetails.sections("expanded-fspl").joinToString { it.second }
        assertTrue(freeSpace.contains("32.4")); assertTrue(freeSpace.contains("ideal"))
        val lte = CellRfReferenceDetails.sections("cell-power").joinToString { it.second }
        assertTrue(lte.contains("−140")); assertTrue(lte.contains("not a service target"))
        assertTrue(CellRfReferenceDetails.sections("expanded-cell-das").joinToString { it.second }.contains("not locate"))
    }
}
