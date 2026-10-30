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
    @Test fun sampleAgeIsAlwaysRelativeToCaptureReceipt() {
        val data = capture()
        val serving = data.getJSONArray("observations").getJSONObject(0).getJSONArray("cells").getJSONObject(0)
        val text = CellularOverview.render(data, plan())
        assertTrue(text.contains("5 ms old at receipt"))
        serving.put("age_ms", 15000)
        assertTrue(CellularOverview.render(data, plan()).contains("15000 ms old at receipt (old sample)"))
        serving.put("age_ms", JSONObject.NULL)
        assertTrue(CellularOverview.render(data, plan()).contains("sample age unknown at receipt"))
    }
    @Test fun retainsOverlappingNrCandidates() {
        val label = CellularOverview.bandLabel("NR", JSONObject().put("nrarfcn",640000), plan())
        assertTrue(label.contains("n48")); assertTrue(label.contains("n77")); assertTrue(label.contains("n78"))
        assertFalse(label.contains("modem reported"))
    }
    @Test fun incompleteNeighborIdentitiesRemainSeparate() {
        val data = capture()
        val cells = data.getJSONArray("observations").getJSONObject(0).getJSONArray("cells")
        val neighbor = cells.getJSONObject(1)
        neighbor.put("identity", JSONObject().put("mcc","310").put("mnc","260"))
        cells.put(JSONObject(neighbor.toString()))
        val text = CellularOverview.render(data, plan())
        assertEquals(2, Regex("sim-1 / Neighbor /").findAll(text).count())
    }
    @Test fun explainsServingMeasurementsWithoutInventingMissingValues() {
        val data = capture()
        val cell = data.getJSONArray("observations").getJSONObject(0).getJSONArray("cells").getJSONObject(0)
        cell.put("signal", JSONObject("""{"rsrp":{"value":-110,"unit":"dBm"},"rsrq":{"value":-16,"unit":"dB"},"rssnr":{"value":2,"unit":"dB"}}"""))
        val original = data.toString()
        val text = CellularOverview.render(data, plan())
        assertEquals(original, data.toString())
        assertTrue(text.contains("RSRP: -110 dBm (Weak)"))
        assertTrue(text.contains("RSRQ: -16 dB (Poor)"))
        assertTrue(text.contains("LTE RSSNR: 2 dB (Marginal)"))
        assertTrue(text.contains("field guidance"))
        assertTrue(text.contains("not a service guarantee"))
    }
    @Test fun showsNrMetricNamesAndDoesNotInterpretWrongUnitsOrNulls() {
        val data = capture()
        val cell = data.getJSONArray("observations").getJSONObject(0).getJSONArray("cells").getJSONObject(0)
        cell.put("radio","NR").put("signal",JSONObject("""{"ss_rsrp":{"value":-101,"unit":"dBm"},"ss_rsrq":{"value":null,"unit":"dB"},"ss_sinr":{"value":15,"unit":"unknown"}}"""))
        val text = CellularOverview.render(data, plan())
        assertTrue(text.contains("NR SS-RSRP: -101 dBm (Weak)"))
        assertTrue(text.contains("NR SS-RSRQ: Not exposed"))
        assertTrue(text.contains("NR SS-SINR: 15 unknown"))
        assertFalse(text.contains("NR SS-SINR: 15 unknown (Good)"))
    }
}
