package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class CellInventoryModelTest {
    private fun row(radio:String, registered:Any, role:String, identity:JSONObject = JSONObject(), signal:JSONObject = JSONObject()) =
        JSONObject().put("radio",radio).put("registered",registered).put("connection_status",role)
            .put("age_ms",5).put("identity",identity).put("signal",signal)
    private fun observation(ms:Long, cells:JSONArray) = JSONObject().put("subscription_key","sim-1").put("elapsed_realtime_ms",ms)
        .put("received_utc","2026-11-05T12:00:00Z").put("cells",cells)
    private fun capture(vararg obs:JSONObject) = JSONObject().put("observations",JSONArray(obs.toList()))
    private val plan = JSONObject().put("ranges", JSONArray())

    @Test fun latestObservationDoesNotPresentOldServingCellsAsCurrent() {
        val old = observation(1, JSONArray().put(row("LTE",true,"primary")))
        val newer = observation(2, JSONArray().put(row("NR",false,"none")))
        val result = CellInventoryModel.build(capture(old,newer),plan)
        assertEquals(1,result.total)
        assertEquals(CellInventoryModel.Group.NEIGHBOR,result.cells.single().group)
        assertEquals("NR",result.cells.single().radio)
    }
    @Test fun showsModemBandProvenanceAndMissingMetricsWithoutChangingEvidence() {
        val id=JSONObject().put("bands",JSONArray().put(13)).put("pci",7).put("cell_id","123")
        val signal=JSONObject().put("rsrp",JSONObject().put("value",-97).put("unit","dBm"))
        val data=capture(observation(10,JSONArray().put(row("LTE",true,"primary",id,signal))))
        val before=data.toString(); val cell=CellInventoryModel.build(data,plan).cells.single()
        assertEquals(before,data.toString())
        assertTrue(cell.band.contains("modem reported"))
        assertTrue(cell.metrics.any { it.contains("RSRP: -97 dBm") })
        assertTrue(cell.metrics.any { it.contains("RSRQ: Not exposed") })
        assertTrue(cell.identity.any { it.contains("PCI: 7") })
        assertTrue(cell.age.contains("5 ms old at receipt"))
    }
    @Test fun conflictingOrUnknownRegistrationDoesNotBecomeNeighbor() {
        val rows=JSONArray().put(row("LTE",false,"primary")).put(row("LTE",JSONObject.NULL,"unknown"))
        val groups=CellInventoryModel.build(capture(observation(10,rows)),plan).cells.map { it.group }
        assertEquals(listOf(CellInventoryModel.Group.UNCLASSIFIED,CellInventoryModel.Group.UNCLASSIFIED),groups)
    }
    @Test fun filteringAndDisplayLimitLeaveTotalExplicit() {
        val rows=JSONArray(); repeat(150) { rows.put(row("GSM",false,"none",JSONObject().put("arfcn",it))) }
        val inventory=CellInventoryModel.build(capture(observation(10,rows)),plan)
        assertEquals(150,inventory.total); assertEquals(128,inventory.cells.size); assertEquals(22,inventory.omitted)
        assertEquals(128,CellInventoryModel.filter(inventory.cells,CellInventoryModel.Group.NEIGHBOR,"gsm").size)
        assertTrue(CellInventoryModel.filter(inventory.cells,CellInventoryModel.Group.SERVING,"").isEmpty())
    }
    @Test fun servingCellsTakePriorityWhenManyNeighborsAreReported() {
        val rows=JSONArray(); repeat(140) { rows.put(row("GSM",false,"none")) }
        rows.put(row("LTE",true,"primary"))
        val inventory=CellInventoryModel.build(capture(observation(10,rows)),plan)
        assertEquals(141,inventory.total)
        assertEquals(CellInventoryModel.Group.SERVING,inventory.cells.first().group)
    }
}
