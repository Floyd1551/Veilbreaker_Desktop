package com.veilbreaker.companion

import org.json.JSONObject
import java.util.Locale

/** Read-only presentation of the most recent observation per subscription. */
object CellInventoryModel {
    enum class Group { SERVING, NEIGHBOR, UNCLASSIFIED }
    data class Cell(val group: Group, val radio: String, val role: String, val subscription: String,
                    val carrier: String, val band: String, val received: String, val age: String,
                    val identity: List<String>, val metrics: List<String>, val cellResponseReceived: String?) {
        fun searchText(): String = (listOf(radio, role, subscription, carrier, band, received, age) + identity + metrics)
            .joinToString(" ").lowercase(Locale.ROOT)
    }
    data class Inventory(val cells: List<Cell>, val total: Int, val omitted: Int)
    private const val LIMIT = 128
    private fun text(value: Any?): String? = when (value) {
        null, JSONObject.NULL -> null
        is String -> value.trim().takeIf { it.isNotEmpty() && it != "null" }?.replace('\n',' ')?.replace('\r',' ')?.take(160)
        is Number -> value.toString()
        else -> null
    }
    private fun item(obj:JSONObject?, key:String) = text(obj?.opt(key))
    private fun role(row:JSONObject): Pair<Group,String> {
        val registered = row.opt("registered")
        val status = row.optString("connection_status")
        return when {
            registered == true && status == "primary" -> Group.SERVING to "Primary serving"
            registered == true && status == "secondary" -> Group.SERVING to "Secondary serving"
            registered == true -> Group.SERVING to "Registered · role not exposed"
            registered == false && status in listOf("primary", "secondary") -> Group.UNCLASSIFIED to "Conflicting role flags"
            registered == false -> Group.NEIGHBOR to "Neighbor / not registered"
            else -> Group.UNCLASSIFIED to "Registration not exposed"
        }
    }
    private val labels = mapOf("rsrp" to "RSRP", "rsrq" to "RSRQ", "rssnr" to "LTE SINR", "rssi" to "RSSI",
        "ss_rsrp" to "SS-RSRP", "ss_rsrq" to "SS-RSRQ", "ss_sinr" to "SS-SINR", "csi_rsrp" to "CSI-RSRP",
        "csi_rsrq" to "CSI-RSRQ", "csi_sinr" to "CSI-SINR", "rscp" to "RSCP", "ecno" to "Ec/No",
        "cqi" to "CQI", "timing_advance" to "Timing advance", "lte_cqi_table_index" to "LTE CQI table",
        "nr_csi_cqi_table_index" to "NR CSI CQI table", "cdma_rssi" to "CDMA RSSI", "evdo_rssi" to "EVDO RSSI",
        "cdma_ecio_tenths_db" to "CDMA Ec/Io", "evdo_ecio_tenths_db" to "EVDO Ec/Io",
        "evdo_snr_index" to "EVDO SNR index", "gsm_bit_error_rate_index" to "GSM BER index")
    private fun metrics(row:JSONObject, radio:String): List<String> {
        val signal = row.optJSONObject("signal")
        val essential = when (radio) { "LTE" -> listOf("rsrp","rsrq","rssnr"); "NR" -> listOf("ss_rsrp","ss_rsrq","ss_sinr"); else -> emptyList() }
        val keys = LinkedHashSet(essential)
        if (signal != null) for (key in signal.keys().asSequence().sorted()) if (key in labels) keys.add(key)
        val values = keys.map { key ->
            val quantity=signal?.optJSONObject(key)
            val raw=quantity?.opt("value") as? Number
            val unit=item(quantity,"unit")
            val valid=raw?.toDouble()?.isFinite() == true && unit != null
            "${labels[key] ?: key}: " + if (valid) "${raw} $unit" else "Not exposed"
        }.toMutableList()
        val report=row.optJSONObject("radio_details")?.optJSONArray("nr_csi_cqi_report")
        if (report != null && report.length() > 0) {
            val entries=(0 until minOf(report.length(),64)).joinToString(", ") { i -> text(report.opt(i)) ?: "—" }
            values.add("NR CSI CQI report: $entries" + if (report.length()>64 || row.optJSONObject("radio_details")?.optBoolean("nr_csi_cqi_truncated") == true) " (truncated)" else "")
        }
        return values.ifEmpty { listOf("Signal measurements not exposed") }
    }
    private fun identity(id:JSONObject?): List<String> {
        val fields=listOf("mcc" to "MCC", "mnc" to "MNC", "cell_id" to "Cell ID", "pci" to "PCI", "tac" to "TAC",
            "earfcn" to "EARFCN", "nrarfcn" to "NR-ARFCN", "bandwidth_khz" to "Bandwidth kHz", "lac" to "LAC",
            "arfcn" to "ARFCN", "uarfcn" to "UARFCN", "bsic" to "BSIC", "psc" to "PSC", "cpid" to "CPID",
            "system_id" to "System ID", "network_id" to "Network ID", "base_station_id" to "Base station ID")
        return fields.mapNotNull { (key,label) -> item(id,key)?.let { "$label: $it" } }.ifEmpty { listOf("Cell identity not exposed") }
    }
    fun build(capture:JSONObject?, plan:JSONObject?): Inventory {
        val observations=capture?.optJSONArray("observations") ?: return Inventory(emptyList(),0,0)
        val latest=linkedMapOf<String,JSONObject>()
        for (i in 0 until minOf(observations.length(),1000)) {
            val obs=observations.optJSONObject(i) ?: continue
            val sub=item(obs,"subscription_key") ?: continue
            val elapsed=(obs.opt("elapsed_realtime_ms") as? Number)?.toLong()?.takeIf { it>=0 } ?: continue
            if (latest[sub] == null || elapsed >= latest.getValue(sub).optLong("elapsed_realtime_ms",-1)) latest[sub]=obs
        }
        val subscriptions=capture.optJSONArray("subscriptions")
        val buckets=Group.entries.associateWith { mutableListOf<Cell>() }
        var total=0
        for ((sub,obs) in latest) {
            val subscription=if(subscriptions==null) null else (0 until minOf(subscriptions.length(),32))
                .mapNotNull { subscriptions.optJSONObject(it) }.firstOrNull { item(it,"key")==sub }
            val cells=obs.optJSONArray("cells") ?: continue
            for (i in 0 until minOf(cells.length(),256)) {
                val row=cells.optJSONObject(i) ?: continue
                total++
                val id=row.optJSONObject("identity"); val radio=item(row,"radio") ?: "Unknown radio"
                val (group,role)=role(row)
                val bucket=buckets.getValue(group)
                if (bucket.size>=LIMIT) continue
                val carrier=item(id,"operator_alpha_long") ?: if(group==Group.SERVING) item(subscription,"network_operator") else null
                val band=if (id!=null && plan!=null && radio in listOf("LTE","NR")) runCatching { CellularOverview.bandLabel(radio,id,plan) }.getOrNull() else null
                val age=(row.opt("age_ms") as? Number)?.toLong()?.takeIf { it>=0 }?.let { "$it ms old at receipt" } ?: "Sample age unavailable at receipt"
                bucket.add(Cell(group,radio,role,sub,carrier ?: "Carrier not exposed",band ?: "Band not exposed",
                    item(obs,"received_utc") ?: "Receipt time unavailable",age,identity(id),metrics(row,radio),item(obs,"cell_response_received_utc")))
            }
        }
        val rows=Group.entries.flatMap { buckets.getValue(it) }.take(LIMIT)
        return Inventory(rows,total,(total-rows.size).coerceAtLeast(0))
    }
    fun filter(cells:List<Cell>, group:Group?, query:String): List<Cell> {
        val words=query.trim().lowercase(Locale.ROOT).split(Regex("\\s+")).filter { it.isNotEmpty() }
        return cells.filter { (group==null || it.group==group) && words.all(it.searchText()::contains) }
    }
}
