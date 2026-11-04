package com.veilbreaker.companion

import org.json.JSONObject

/** A presentation-only view of saved capture evidence. Never modifies an envelope. */
object CellularDashboard {
    data class Point(val elapsedMs: Long, val value: Double)
    data class Metric(val name: String, val value: Double?, val unit: String, val low: Float, val high: Float)
    data class Card(val context: String, val receivedUtc: String, val age: String,
                    val metrics: List<Metric>, val trend: List<Point>)

    private fun text(obj: JSONObject?, key: String): String? {
        if (obj == null || !obj.has(key) || obj.isNull(key)) return null
        return obj.optString(key).takeIf { it.isNotBlank() && it != "null" }
    }

    private fun value(cell: JSONObject, key: String, unit: String): Double? {
        val quantity = cell.optJSONObject("signal")?.optJSONObject(key) ?: return null
        if (quantity.optString("unit") != unit) return null
        val number = quantity.opt("value") as? Number ?: return null
        val range = when (key) {
            "rsrp", "ss_rsrp" -> -160.0..-20.0
            "rsrq" -> -50.0..20.0
            "ss_rsrq" -> -50.0..30.0
            "rssnr" -> -30.0..50.0
            "ss_sinr" -> -30.0..60.0
            else -> return null
        }
        return number.toDouble().takeIf { it.isFinite() && it in range }
    }

    private fun identity(cell: JSONObject): String? {
        val id = cell.optJSONObject("identity")
        val mcc = text(id,"mcc") ?: return null
        val mnc = text(id,"mnc") ?: return null
        val cellId = text(id,"cell_id") ?: return null
        val radio = text(cell,"radio") ?: return null
        return "$radio/$mcc/$mnc/$cellId"
    }

    fun build(envelope: JSONObject, plan: JSONObject? = null): List<Card> {
        val all = envelope.optJSONArray("observations") ?: return emptyList()
        val observations = (0 until all.length()).mapNotNull { all.optJSONObject(it) }
        val subscriptions=envelope.optJSONArray("subscriptions")
        val latest = linkedMapOf<String,JSONObject>()
        for (obs in observations) {
            val sub = text(obs,"subscription_key") ?: continue
            val elapsed = obs.optLong("elapsed_realtime_ms", -1)
            if (elapsed < 0) continue
            if (latest[sub] == null || elapsed >= latest.getValue(sub).optLong("elapsed_realtime_ms",-1)) latest[sub]=obs
        }
        val cards = mutableListOf<Card>()
        subscriptionsLoop@ for ((sub, obs) in latest) {
            val cells = obs.optJSONArray("cells") ?: continue
            for (index in 0 until cells.length()) {
                val cell = cells.optJSONObject(index) ?: continue
                val radio = cell.optString("radio")
                if (!cell.optBoolean("registered",false) || radio !in listOf("LTE","NR")) continue
                // Only eight cards are displayed; keep one extra solely to indicate omission.
                if (cards.size >= 9) break@subscriptionsLoop
                val power = if (radio == "NR") "ss_rsrp" else "rsrp"
                val quality = if (radio == "NR") "ss_rsrq" else "rsrq"
                val sinr = if (radio == "NR") "ss_sinr" else "rssnr"
                val metrics = listOf(Metric(if (radio == "NR") "SS-RSRP" else "RSRP", value(cell,power,"dBm"),"dBm",-140f,-60f),
                    Metric(if (radio == "NR") "SS-RSRQ" else "RSRQ",value(cell,quality,"dB"),"dB",-25f,-5f),
                    Metric(if (radio == "NR") "SS-SINR" else "SINR",value(cell,sinr,"dB"),"dB",-10f,30f))
                val role = when (cell.optString("connection_status")) { "primary" -> "Primary serving"; "secondary" -> "Secondary serving"; else -> "Registered; role unavailable" }
                val id = cell.optJSONObject("identity")
                val band = if (plan != null && id != null) runCatching { CellularOverview.bandLabel(radio,id,plan) }.getOrNull() else null
                val subscription = if(subscriptions == null) null else (0 until subscriptions.length())
                    .mapNotNull { subscriptions.optJSONObject(it) }.firstOrNull { text(it,"key") == sub }
                val carrier = text(id,"operator_alpha_long") ?: text(subscription,"network_operator")
                    ?: text(subscription,"sim_carrier")?.let { "$it (SIM carrier)" } ?: "Carrier not exposed"
                val context = listOf("$radio · $role",carrier,band,"$sub · cell ${text(id,"cell_id") ?: "not exposed"} · PCI ${text(id,"pci") ?: "not exposed"}").filterNotNull().joinToString("\n")
                val ageNum = cell.opt("age_ms") as? Number
                val age = ageNum?.toLong()?.takeIf { it >= 0 }?.let { "$it ms old at receipt" } ?: "Sample age unavailable at receipt"
                val targetId = identity(cell)
                val points = sortedMapOf<Long,Double>()
                val conflicts = mutableSetOf<Long>()
                if (targetId != null) for (sample in observations) {
                    if (text(sample,"subscription_key") != sub) continue
                    val array = sample.optJSONArray("cells") ?: continue
                    var row: JSONObject? = null
                    var ambiguous = false
                    for (candidateIndex in 0 until array.length()) {
                        val candidate=array.optJSONObject(candidateIndex) ?: continue
                        if (candidate.optBoolean("registered",false) && identity(candidate) == targetId) {
                            if(row != null) { ambiguous=true;break }
                            row=candidate
                        }
                    }
                    if (ambiguous || row == null) continue
                    val elapsed=sample.optLong("elapsed_realtime_ms",-1)
                    val rowAge=(row.opt("age_ms") as? Number)?.toLong() ?: continue
                    if (elapsed < 0 || rowAge < 0 || rowAge > elapsed) continue
                    val v=value(row,power,"dBm") ?: continue
                    // Repeated modem timestamps are cached observations, not new samples.
                    val stamp=elapsed-rowAge
                    if (stamp in conflicts) continue
                    val prior=points[stamp]
                    if (prior != null && prior != v) { points.remove(stamp); conflicts.add(stamp) }
                    else points[stamp]=v
                }
                cards.add(Card(context,text(obs,"received_utc") ?: "Time unavailable",age,metrics,points.map { Point(it.key,it.value) }))
            }
        }
        return cards
    }
}
