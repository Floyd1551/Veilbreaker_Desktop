package com.veilbreaker.companion

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class LiveCellTrendTest {
    private fun cell(id: String? = "123", age: Long? = 1000, power: Int? = -90,
                     channel: Int? = 5230, radio: String = "LTE", role: String = "primary"): JSONObject {
        val identity = JSONObject().put("mcc", "311").put("mnc", "480")
        if (id != null) identity.put("cell_id", id)
        if (channel != null) identity.put(if (radio == "LTE") "earfcn" else "nrarfcn", channel)
        identity.put("pci", 23)
        val signal = JSONObject()
        if (power != null) signal.put(if (radio == "LTE") "rsrp" else "ss_rsrp", JSONObject().put("value", power).put("unit", "dBm"))
        return JSONObject().put("radio", radio).put("registered", true).put("connection_status", role)
            .put("identity", identity).put("signal", signal).put("age_ms", age ?: JSONObject.NULL)
    }

    @Test fun repeatedTimestampIsNotANewReading() {
        val history = LiveCellTrend()
        history.accept(listOf(cell(age=1000)), 100000)
        history.accept(listOf(cell(age=11000)), 110000)
        assertEquals(1, history.points.size)
        assertTrue(history.status.contains("repeated", ignoreCase = true))
        history.accept(listOf(cell(age=1000, power=-88)), 120000)
        assertEquals(listOf(-90.0, -88.0), history.points.map { it.value })
    }

    @Test fun differentOrAmbiguousIdentityIsNeverJoined() {
        val history = LiveCellTrend()
        history.accept(listOf(cell()), 100000)
        history.accept(listOf(cell(id="456")), 110000)
        assertEquals(1, history.points.size)
        history.accept(listOf(cell(id=null)), 120000)
        assertTrue(history.points.isEmpty())
        history.accept(listOf(cell(), cell(id="456")), 130000)
        assertTrue(history.points.isEmpty())
        history.accept(listOf(cell()), 140000)
        history.accept(listOf(cell(channel=6000)), 150000)
        assertEquals(1, history.points.size)
    }

    @Test fun unavailableStaleOrConflictingSamplesBreakTheHistory() {
        val history = LiveCellTrend()
        history.accept(listOf(cell()), 100000)
        history.accept(listOf(cell(age=30000)), 110000)
        assertTrue(history.points.isEmpty())
        history.accept(listOf(cell()), 120000)
        history.accept(listOf(cell(age=11000, power=-77)), 130000)
        assertTrue(history.points.isEmpty())
        history.accept(listOf(cell(age=null)), 140000)
        assertTrue(history.points.isEmpty())
        history.accept(emptyList(), 150000)
        assertTrue(history.points.isEmpty())
    }

    @Test fun secondaryOnlyIsUsableWhenItIsTheOnlyRegisteredCell() {
        val history=LiveCellTrend()
        history.accept(listOf(cell(role="none")), 100000)
        assertEquals(1, history.points.size)
        assertTrue(history.status.contains("registered", ignoreCase=true))
        history.reset()
        assertTrue(history.points.isEmpty())
    }

    @Test fun historyIsBoundedAndDoesNotMutateEvidence() {
        val history=LiveCellTrend()
        val row=cell(); val before=row.toString()
        repeat(40) { history.accept(listOf(row), 100000L+it*10000L) }
        assertEquals(30, history.points.size)
        assertEquals(before, row.toString())
    }

    @Test fun longGapStartsANewSeriesAndNrUsesSsRsrp() {
        val history=LiveCellTrend()
        history.accept(listOf(cell(radio="NR", channel=630000)), 100000)
        assertEquals("SS-RSRP", history.metric)
        history.accept(listOf(cell(radio="NR", channel=630000)), 151000)
        assertEquals(1, history.points.size)
        assertTrue(history.status.contains("restarted"))
    }
}
