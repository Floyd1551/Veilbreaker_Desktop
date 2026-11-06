package com.veilbreaker.companion

import org.json.JSONObject

/** Select complete identities without combining cells, inferring fields, or sending data. */
object OpenCellCapturePicker {
    data class Candidate(val radio: String, val mcc: String, val mnc: String, val area: String,
                         val cellId: String, val subscription: String, val received: String, val role: String,
                         val ageAtReceipt: Long?) {
        val label: String get() = "$radio · $role · $subscription\n$mcc/$mnc · TAC $area · cell $cellId\nReceived $received · " +
            (ageAtReceipt?.let { "$it ms old at receipt" } ?: "sample age unavailable")
    }
    data class Options(val candidates: List<Candidate>, val incomplete: Int, val truncated: Boolean)

    fun options(capture: JSONObject?): Options {
        val observations = capture?.optJSONArray("observations") ?: return Options(emptyList(), 0, false)
        val latest = linkedMapOf<String, JSONObject>()
        for (i in 0 until minOf(observations.length(), 4096)) {
            val obs = observations.optJSONObject(i) ?: continue
            val sub = (obs.opt("subscription_key") as? String)?.takeIf { it.isNotBlank() } ?: continue
            val elapsed = (obs.opt("elapsed_realtime_ms") as? Number)?.toLong()?.takeIf { it >= 0 } ?: continue
            val old = latest[sub]
            if (old == null || elapsed >= old.optLong("elapsed_realtime_ms", -1)) latest[sub] = obs
        }
        var incomplete = 0
        var truncated = observations.length() > 4096
        val out = mutableListOf<Candidate>()
        for ((subscription, obs) in latest) {
            val cells = obs.optJSONArray("cells") ?: continue
            if (cells.length() > 4096) truncated = true
            for (i in 0 until minOf(cells.length(), 4096)) {
                val row = cells.optJSONObject(i) ?: continue
                val radio = row.optString("radio")
                if (row.opt("registered") != true || radio !in listOf("LTE", "NR")) continue
                val id = row.optJSONObject("identity")
                fun field(name: String): String = id?.opt(name)?.takeUnless { it == JSONObject.NULL }?.toString().orEmpty()
                val mcc = field("mcc"); val mnc = field("mnc"); val tac = field("tac"); val cellId = field("cell_id")
                if (OpenCellLookup.query(mcc, mnc, tac, cellId, radio) == null) { incomplete++; continue }
                if (out.size == 64) { truncated = true; continue }
                val role = when (row.optString("connection_status")) {
                    "primary" -> "Primary serving"
                    "secondary" -> "Secondary serving"
                    else -> "Registered; role unavailable"
                }
                fun safe(value: String) = value.filterNot { it.isISOControl() }.take(60).ifBlank { "unavailable" }
                val age = (row.opt("age_ms") as? Number)?.toLong()?.takeIf { it >= 0 }
                out.add(Candidate(radio, mcc, mnc, tac, cellId, safe(subscription), safe(obs.optString("received_utc", "unavailable")), role, age))
            }
        }
        return Options(out, incomplete, truncated)
    }
}
