package com.veilbreaker.companion

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class ServingCellChangeTrackerTest {
    private fun cell(id: String? = "123", age: Long? = 1000, radio: String = "LTE",
                     pci: Int? = 23, channel: Int? = 5230, role: String = "primary"): JSONObject {
        val identity = JSONObject().put("mcc", "311").put("mnc", "480")
        if (id != null) identity.put("cell_id", id)
        if (pci != null) identity.put("pci", pci)
        if (channel != null) identity.put(if (radio == "LTE") "earfcn" else "nrarfcn", channel)
        return JSONObject().put("radio", radio).put("registered", true).put("connection_status", role)
            .put("identity", identity).put("age_ms", age ?: JSONObject.NULL)
    }
    private fun add(t: ServingCellChangeTracker, row: JSONObject, now: Long, sub: String = "sim1") =
        t.accept(sub, listOf(row), now, "2026-11-20T12:00:00Z")

    @Test fun onlyDistinctFreshCompleteIdentitiesCreateEvents() {
        val t = ServingCellChangeTracker("sim1")
        val row = cell(); val original = row.toString()
        add(t, row, 100000); add(t, cell(age=11000), 110000)
        assertTrue(t.events.isEmpty())
        add(t, cell(id="456"), 120000)
        assertEquals(1, t.events.size)
        val event = t.events.single()
        assertEquals("123", event.previous.cellId); assertEquals("456", event.current.cellId)
        assertEquals(119000, event.sampleElapsedMs); assertEquals(1000, event.ageAtReceiptMs)
        assertEquals("2026-11-20T12:00:00Z", event.receivedUtc)
        assertEquals("primary", event.previousRole); assertEquals("primary", event.currentRole)
        assertTrue(event.source.contains("Android"))
        assertEquals(original, row.toString())
    }

    @Test fun unknownAmbiguousStaleAndOutOfOrderBreakContinuity() {
        val t = ServingCellChangeTracker("sim1")
        add(t, cell(), 100000); add(t, cell(id=null), 110000); add(t, cell(id="456"), 120000)
        assertTrue(t.events.isEmpty())
        add(t, cell(id="789", age=30000), 130000); add(t, cell(id="999"), 140000)
        assertTrue(t.events.isEmpty())
        t.accept("sim1", listOf(cell(id="1"),cell(id="2")),150000,"2026-11-20T12:00:00Z")
        add(t,cell(id="3"),160000); assertTrue(t.events.isEmpty())
        add(t,cell(id="4",age=11000),170000); add(t,cell(id="5"),180000)
        assertTrue(t.events.isEmpty())
        add(t,cell(id="6"),190000); assertEquals(1,t.events.size)
    }

    @Test fun sameTimestampConflictAndLongGapCannotBecomeAChange() {
        val t = ServingCellChangeTracker("sim1")
        add(t,cell(id="1"),100000); add(t,cell(id="2",age=11000),110000)
        add(t,cell(id="3"),120000); assertTrue(t.events.isEmpty())
        add(t,cell(id="4"),200000); assertTrue(t.events.isEmpty())
        add(t,cell(id="5"),210000); assertEquals(1,t.events.size)
    }

    @Test fun olderResponseAfterACachedRepeatCannotCreateAChange() {
        val t = ServingCellChangeTracker("sim1")
        add(t,cell(id="1"),100000)
        add(t,cell(id="1",age=11000),110000)
        add(t,cell(id="2"),105000)
        add(t,cell(id="3"),120000)
        assertTrue(t.events.isEmpty())
    }

    @Test fun oversizedResponsesBreakContinuityRatherThanChoosePartialData() {
        val t = ServingCellChangeTracker("sim1")
        add(t,cell(id="1"),100000)
        t.accept("sim1", List(257) { cell(id=(it+2).toString()) }, 110000, null)
        add(t,cell(id="3"),120000)
        assertTrue(t.events.isEmpty())
    }

    @Test fun selectedSubscriptionAndServingRoleStaySeparate() {
        val t = ServingCellChangeTracker("sim1")
        add(t,cell(id="1"),100000); add(t,cell(id="8"),110000,sub="sim2")
        add(t,cell(id="2"),120000); assertEquals(1,t.events.size)
        add(t,cell(id="3",role="secondary"),130000)
        add(t,cell(id="4",role="none"),140000); assertEquals(1,t.events.size)
        add(t,cell(id="4",role="primary"),150000); assertEquals(1,t.events.size)
        add(t,cell(id="5",role="none"),160000); assertEquals(2,t.events.size)
        assertEquals("primary", t.events.last().previousRole)
        assertEquals("registered_role_unconfirmed", t.events.last().currentRole)
    }

    @Test fun eventsAreBoundedAndSessionResetIsExplicit() {
        val t = ServingCellChangeTracker("sim1")
        repeat(65) { add(t,cell(id=(it+1).toString()),100000L+it*1000L) }
        assertEquals(50,t.events.size)
        t.reset(); assertTrue(t.events.isEmpty())
    }

    @Test fun invalidRangeOrUnexposedIdentityNeverProducesAnEvent() {
        val t = ServingCellChangeTracker("sim1")
        add(t,cell(id="1"),100000)
        add(t,cell(id="268435456"),110000)
        add(t,cell(id="2",pci=504),120000)
        add(t,cell(id="3",channel=null),130000)
        add(t,cell(id="4"),140000)
        assertTrue(t.events.isEmpty())
    }
}
