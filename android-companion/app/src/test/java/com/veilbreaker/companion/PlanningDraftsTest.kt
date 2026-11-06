package com.veilbreaker.companion

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class PlanningDraftsTest {
    @Test fun wifiRoundTripsPartialOperatorInputsWithoutResults() {
        val draft = PlanningWifiDraft("1000", "10", "", "25")
        val encoded = PlanningDraftCodec.encodeWifi(draft)!!
        assertEquals(draft, PlanningDraftCodec.decodeWifi(encoded))
        val record = JSONObject(encoded)
        assertEquals("operator_entered", record.getString("provenance"))
        assertFalse(record.has("result"))
        assertFalse(record.has("evidence"))
    }

    @Test fun fwaRoundTripsCoordinatesAndFrequency() {
        val draft = PlanningFwaDraft("37.5", "-122.25", "38", "-121", "3500")
        assertEquals(draft, PlanningDraftCodec.decodeFwa(PlanningDraftCodec.encodeFwa(draft)))
    }

    @Test fun invalidInputCannotBeSaved() {
        assertNull(PlanningDraftCodec.encodeWifi(PlanningWifiDraft("NaN", "10", "0", "1")))
        assertNull(PlanningDraftCodec.encodeWifi(PlanningWifiDraft("1", "10", "1.5", "1")))
        assertNull(PlanningDraftCodec.encodeWifi(PlanningWifiDraft("1", "0", "1", "1")))
        assertNull(PlanningDraftCodec.encodeFwa(PlanningFwaDraft("91", "", "", "", "")))
        assertNull(PlanningDraftCodec.encodeFwa(PlanningFwaDraft("", "", "", "", "Infinity")))
        assertNull(PlanningDraftCodec.encodeFwa(PlanningFwaDraft("", "", "", "", "10000001")))
    }

    @Test fun corruptOrUnrecognizedRecordsAreRejected() {
        val valid = JSONObject(PlanningDraftCodec.encodeWifi(PlanningWifiDraft("1", "", "", ""))!!)
        assertNull(PlanningDraftCodec.decodeWifi("not json"))
        assertNull(PlanningDraftCodec.decodeWifi(JSONObject(valid.toString()).put("schema_version", 2).toString()))
        assertNull(PlanningDraftCodec.decodeWifi(JSONObject(valid.toString()).put("provenance", "measured").toString()))
        assertNull(PlanningDraftCodec.decodeFwa(valid.toString()))
        assertNull(PlanningDraftCodec.decodeWifi(JSONObject(valid.toString()).put("inputs", JSONObject().put("area_m2", "1")).toString()))
        assertNull(PlanningDraftCodec.decodeWifi(JSONObject(valid.toString()).put("inputs", valid.getJSONObject("inputs").put("area_m2", "-1")).toString()))
    }
}
