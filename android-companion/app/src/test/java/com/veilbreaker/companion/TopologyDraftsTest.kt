package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class TopologyDraftsTest {
    @Test fun roundTripsOperatorSketchAndEmptyDraft() {
        val state = TopologyEditor.State(listOf("Router", "Switch", "AP"), listOf(0 to 1, 1 to 2))
        val encoded = TopologyDraftCodec.encode(state)!!
        assertEquals(state, TopologyDraftCodec.decode(encoded))
        assertEquals("operator_entered", JSONObject(encoded).getString("provenance"))
        assertFalse(JSONObject(encoded).has("measurement"))
        assertEquals(TopologyEditor.State(), TopologyDraftCodec.decode(TopologyDraftCodec.encode(TopologyEditor.State())))
    }

    @Test fun rejectsInvalidGraphsAndMalformedRecords() {
        assertNull(TopologyDraftCodec.encode(TopologyEditor.State(listOf("A", "A"))))
        assertNull(TopologyDraftCodec.encode(TopologyEditor.State(listOf("A"), listOf(0 to 1))))
        assertNull(TopologyDraftCodec.encode(TopologyEditor.State(listOf("A", "B"), listOf(0 to 1, 1 to 0))))
        val valid = TopologyDraftCodec.encode(TopologyEditor.State(listOf("A", "B"), listOf(0 to 1)))!!
        assertNull(TopologyDraftCodec.decode("not json"))
        assertNull(TopologyDraftCodec.decode(JSONObject(valid).put("schema_version", 2).toString()))
        assertNull(TopologyDraftCodec.decode(JSONObject(valid).put("provenance", "measured").toString()))
        assertNull(TopologyDraftCodec.decode(JSONObject(valid).put("links", JSONArray().put(JSONArray().put(0.5).put(1))).toString()))
        assertNull(TopologyDraftCodec.decode(JSONObject(valid).put("nodes", JSONArray().put("A").put(" A ")).toString()))
        assertNull(TopologyDraftCodec.decode("x".repeat(16385)))
    }
}
