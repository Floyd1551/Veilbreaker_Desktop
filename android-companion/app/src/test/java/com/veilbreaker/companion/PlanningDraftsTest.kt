package com.veilbreaker.companion

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
import java.time.Instant

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

    @Test fun fwaPreservesVerifiedCandidateAndRejectsMismatchedCoordinates() {
        val source = OpenCellLookup.LocatedCandidate(OpenCellLookup.Query(311, 480, 123, 456, "LTE"),
            OpenCellLookup.Candidate(38.0, -121.0, 10, 250), Instant.parse("2026-11-11T12:00:00Z"))
        val draft = PlanningFwaDraft("37.5", "-122.25", "38", "-121", "3500", source)
        val encoded = PlanningDraftCodec.encodeFwa(draft)!!
        assertEquals("operator_and_reference", JSONObject(encoded).getString("provenance"))
        assertEquals(draft, PlanningDraftCodec.decodeFwa(encoded))
        val altered = JSONObject(encoded)
        altered.getJSONObject("inputs").put("site_latitude", "39")
        assertNull(PlanningDraftCodec.decodeFwa(altered.toString()))
        assertNull(PlanningDraftCodec.encodeFwa(draft.copy(siteLongitude = "-120")))
        assertNull(PlanningDraftCodec.encodeFwa(draft.copy(antennaLatitude = "", siteLongitude = "-120")))
        val missing = JSONObject(encoded).apply { remove("candidate_source") }
        assertNull(PlanningDraftCodec.decodeFwa(missing.toString()))
        val wrongProvider = JSONObject(encoded)
        wrongProvider.getJSONObject("candidate_source").put("provider", "unknown")
        assertNull(PlanningDraftCodec.decodeFwa(wrongProvider.toString()))
        val invalidTime = JSONObject(encoded)
        invalidTime.getJSONObject("candidate_source").put("retrieved_utc", "not-a-time")
        assertNull(PlanningDraftCodec.decodeFwa(invalidTime.toString()))
    }

    @Test fun legacyFwaDraftLoadsWithoutInventingSource() {
        val legacy = JSONObject().put("format", "veilbreaker.android.planning_draft").put("schema_version", 1)
            .put("provenance", "operator_entered").put("kind", "fwa")
            .put("inputs", JSONObject().put("antenna_latitude", "37.5").put("antenna_longitude", "-122.25")
                .put("site_latitude", "38").put("site_longitude", "-121").put("frequency_mhz", "3500"))
        assertNull(PlanningDraftCodec.decodeFwa(legacy.toString())!!.candidateSource)
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
