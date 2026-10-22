package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import org.json.JSONArray
import java.io.File

class CellularOverviewTest {
    private fun plan() = JSONObject(File("../../src/veilbreaker/assets/cellular/channel-bands.json").readText())
    private fun capture(): JSONObject {
        val serving = JSONObject("""{"radio":"LTE","registered":true,"connection_status":"primary","age_ms":5,"identity":{"bands":[13],"cell_id":"123","pci":0},"signal":{"rsrp":{"value":-95,"unit":"dBm"}}}""")
        val neighbor = JSONObject("""{"radio":"LTE","registered":false,"connection_status":"none","age_ms":5,"identity":{"earfcn":5230,"pci":491},"signal":{}}""")
        return JSONObject().put("observations", JSONArray().put(JSONObject().put("observation_id","one").put("subscription_key","sim-1").put("elapsed_realtime_ms",10000).put("received_utc","2026-10-22T12:00:00Z").put("cells",JSONArray().put(serving).put(neighbor))))
    }
    @Test fun showsServingNeighborsAndBandSources() {
        val text = CellularOverview.render(capture(), plan())
        assertTrue(text.contains("Primary serving"))
        assertTrue(text.contains("Neighbor"))
        assertTrue(text.contains("B13 (modem reported)"))
        assertTrue(text.contains("B13 (channel-derived candidates)"))
        assertTrue(text.contains("PCI 491"))
        assertTrue(text.contains("RSRP: -95 dBm"))
    }
    @Test fun doesNotKeepOldConnectionAsCurrent() {
        val data = capture()
        data.getJSONArray("observations").put(JSONObject().put("observation_id","two").put("subscription_key","sim-1").put("elapsed_realtime_ms",15000).put("received_utc","2026-10-22T12:00:05Z").put("cells",JSONArray()))
        val text = CellularOverview.render(data, plan())
        assertTrue(text.contains("No connected cells reported in latest observation"))
        assertTrue(text.contains("earlier observation"))
    }
    @Test fun retainsOverlappingNrCandidates() {
        val label = CellularOverview.bandLabel("NR", JSONObject().put("nrarfcn",640000), plan())
        assertTrue(label.contains("n48")); assertTrue(label.contains("n77")); assertTrue(label.contains("n78"))
        assertFalse(label.contains("modem reported"))
    }
}
