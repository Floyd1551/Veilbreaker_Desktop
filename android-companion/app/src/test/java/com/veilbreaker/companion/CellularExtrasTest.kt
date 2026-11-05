package com.veilbreaker.companion

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class CellularExtrasTest {
    @Test fun unavailableAndNegativeIdentityValuesAreNull() {
        val identity = JSONObject()
        CellularExtras.identityInteger(identity, "lac", Int.MAX_VALUE)
        CellularExtras.identityInteger(identity, "arfcn", -1)
        CellularExtras.identityInteger(identity, "bsic", 0)
        assertTrue(identity.isNull("lac")); assertTrue(identity.isNull("arfcn"))
        assertEquals(0, identity.getInt("bsic"))
    }
    @Test fun cellIdIsPreservedAsTextForDesktopContract() {
        val identity = JSONObject()
        CellularExtras.cellId(identity, 12345)
        assertEquals("12345", identity.getString("cell_id"))
        CellularExtras.cellId(identity, Int.MAX_VALUE)
        assertTrue(identity.isNull("cell_id"))
    }
    @Test fun cqiReportRetainsOrderAndMarksInvalidPositions() {
        val details = JSONObject()
        CellularExtras.nrCqiReport(details, listOf(0, 15, Int.MAX_VALUE, null, 4))
        val report = details.getJSONArray("nr_csi_cqi_report")
        assertEquals(5, report.length()); assertEquals(0, report.getInt(0)); assertEquals(15, report.getInt(1))
        assertTrue(report.isNull(2)); assertTrue(report.isNull(3)); assertEquals(4, report.getInt(4))
    }
    @Test fun emptyCqiIsNotInventedAndOversizeIsExplicitlyTruncated() {
        val details = JSONObject()
        CellularExtras.nrCqiReport(details, emptyList())
        assertFalse(details.has("nr_csi_cqi_report"))
        CellularExtras.nrCqiReport(details, List(65) { 3 })
        assertEquals(64, details.getJSONArray("nr_csi_cqi_report").length())
        assertTrue(details.getBoolean("nr_csi_cqi_truncated"))
    }
}
