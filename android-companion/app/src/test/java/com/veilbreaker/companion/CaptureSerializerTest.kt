package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import java.io.File

class CaptureSerializerTest {
    @Test fun unavailableIsNullAndHasReason() {
        val quantity = CaptureSerializer.quantity(Int.MAX_VALUE, "dBm", -160, -20)
        assertTrue(quantity.isNull("value"))
        assertEquals("not_reported", quantity.getString("reason"))
    }
    @Test fun timestampsAreNotInvented() {
        assertNull(CaptureSerializer.age(100, 101))
        assertNull(CaptureSerializer.age(100, 0))
        assertEquals(15L, CaptureSerializer.age(100, 85))
    }
    @Test fun exportFixtureForDesktopContract() {
        val cell = JSONObject().put("radio", "LTE").put("registered", true).put("connection_status", "primary")
            .put("age_ms", 1500).put("identity", JSONObject().put("cell_id", "1234"))
            .put("signal", JSONObject().put("rsrp", CaptureSerializer.quantity(-95, "dBm", -160, -20)))
        val capture = CaptureSerializer.envelope("Synthetic", "JVM fixture", "13", 33, "test", listOf(cell), 10000L, "complete", emptyList())
        assertFalse(capture.getJSONArray("observations").getJSONObject(0).has("location"))
        val file = File("build/contract-fixture.json")
        file.parentFile.mkdirs(); file.writeText(capture.toString(2))
    }
}
