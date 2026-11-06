package com.veilbreaker.companion

import org.json.JSONObject

/** Candidates from the latest saved observation per subscription, never a fresh phone read. */
object FwaCapturePicker {
    data class Context(val description: String, val identity: Map<String, String>)
    data class Candidate(val context: Context, val rsrp: Double?, val rsrq: Double?, val sinr: Double?) {
        val description: String get() = context.description
    }
    // Unknown identity is not evidence of incompatibility or proof of comparability.
    fun comparable(a: Context?, b: Context?): Boolean = a == null || b == null ||
        a.identity.keys.intersect(b.identity.keys).none { a.identity[it] != b.identity[it] }
    data class Options(val candidates: List<Candidate>, val truncated: Boolean)

    fun options(capture: JSONObject?): Options {
        val observations = capture?.optJSONArray("observations") ?: return Options(emptyList(), false)
        val latest = linkedMapOf<String, JSONObject>()
        for (i in 0 until minOf(observations.length(), 4096)) {
            val obs = observations.optJSONObject(i) ?: continue
            val sub = (obs.opt("subscription_key") as? String)?.takeIf { it.isNotBlank() } ?: continue
            val elapsed = (obs.opt("elapsed_realtime_ms") as? Number)?.toLong()?.takeIf { it >= 0 } ?: continue
            if (latest[sub] == null || elapsed >= latest.getValue(sub).optLong("elapsed_realtime_ms", -1)) latest[sub] = obs
        }
        var truncated = observations.length() > 4096
        val result = mutableListOf<Candidate>()
        fun safe(value: Any?): String = value?.takeUnless { it == JSONObject.NULL }?.toString()
            ?.filterNot { it.isISOControl() }?.take(120)?.takeIf { it.isNotBlank() } ?: "unavailable"
        for ((sub, obs) in latest) {
            val cells = obs.optJSONArray("cells") ?: continue
            if (cells.length() > 4096) truncated = true
            for (i in 0 until minOf(cells.length(), 4096)) {
                val cell = cells.optJSONObject(i) ?: continue
                val radio = cell.optString("radio")
                if (cell.opt("registered") != true || radio !in listOf("LTE", "NR")) continue
                val signal = cell.optJSONObject("signal")
                fun metric(key: String, unit: String, range: ClosedFloatingPointRange<Double>): Double? {
                    val quantity = signal?.optJSONObject(key) ?: return null
                    if (quantity.optString("unit") != unit) return null
                    return (quantity.opt("value") as? Number)?.toDouble()?.takeIf { it.isFinite() && it in range }
                }
                val nr = radio == "NR"
                val rsrp = metric(if (nr) "ss_rsrp" else "rsrp", "dBm", -160.0..-20.0)
                val rsrq = metric(if (nr) "ss_rsrq" else "rsrq", "dB", -50.0..(if (nr) 30.0 else 20.0))
                val sinr = metric(if (nr) "ss_sinr" else "rssnr", "dB", -30.0..(if (nr) 60.0 else 50.0))
                if (rsrp == null && rsrq == null && sinr == null) continue
                if (result.size >= 64) { truncated = true; continue }
                val id = cell.optJSONObject("identity")
                val identity = listOf("mcc", "mnc", "tac", "cell_id", "pci", if (nr) "nrarfcn" else "earfcn", "bands")
                    .joinToString(" · ") { "$it ${safe(id?.opt(it))}" }
                val age = (cell.opt("age_ms") as? Number)?.toLong()?.takeIf { it >= 0 }
                    ?.let { "$it ms old at receipt" } ?: "sample age unavailable"
                val role = when (cell.optString("connection_status")) {
                    "primary" -> "primary serving"; "secondary" -> "secondary serving"; else -> "registered; role unavailable"
                }
                val description = "Saved phone capture ${safe(capture.opt("capture_id"))} · observation ${safe(obs.opt("observation_id"))}\n" +
                    "Received ${safe(obs.opt("received_utc"))} · $age · subscription ${safe(sub)}\n" +
                    "$radio · $role · $identity" + if (nr) "\nNR values are SS-RSRP, SS-RSRQ and SS-SINR." else "\nLTE values are RSRP, RSRQ and RSSNR."
                val keys = linkedMapOf("radio" to radio, "subscription" to sub)
                for (key in listOf("mcc", "mnc", "tac", "cell_id", "pci", if (nr) "nrarfcn" else "earfcn", "bands")) {
                    val value = id?.opt(key)
                    if (value != null && value != JSONObject.NULL && value.toString().isNotBlank() && value.toString() != "[]") keys[key] = value.toString()
                }
                result.add(Candidate(Context(description, keys), rsrp, rsrq, sinr))
            }
        }
        return Options(result, truncated)
    }
}
