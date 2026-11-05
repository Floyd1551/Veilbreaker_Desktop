package com.veilbreaker.companion

import org.json.JSONObject

/** Compact presentation of the most recent recorded Android observations. */
object LiveOverviewModel {
    data class Value(val label: String, val value: Double?, val unit: String)
    data class Cell(val title: String, val carrier: String, val band: String, val channel: String,
                    val pci: String, val age: String, val receivedUtc: String?, val values: List<Value>)
    data class Overview(val receivedUtc: String?, val cells: List<Cell>, val gps: String?)

    private fun text(obj: JSONObject?, key: String): String? {
        if (obj == null || !obj.has(key) || obj.isNull(key)) return null
        return obj.optString(key).takeIf { it.isNotBlank() && it != "null" }
    }

    private fun metric(signal: JSONObject?, key: String, label: String, unit: String, range: ClosedFloatingPointRange<Double>): Value {
        val quantity = signal?.optJSONObject(key)
        val value = if (quantity?.optString("unit") == unit) (quantity.opt("value") as? Number)?.toDouble() else null
        return Value(label, value?.takeIf { it.isFinite() && it in range }, unit)
    }

    fun build(capture: JSONObject?, plan: JSONObject?): Overview {
        val observations = capture?.optJSONArray("observations") ?: return Overview(null, emptyList(), null)
        val subscriptions = capture.optJSONArray("subscriptions")
        val latest = linkedMapOf<String, JSONObject>()
        var latestObservation: JSONObject? = null
        for (i in 0 until minOf(observations.length(), 4096)) {
            val obs = observations.optJSONObject(i) ?: continue
            val elapsed = obs.optLong("elapsed_realtime_ms", -1)
            if (elapsed < 0) continue
            val key = text(obs, "subscription_key") ?: continue
            if (latest[key] == null || elapsed >= latest.getValue(key).optLong("elapsed_realtime_ms", -1)) latest[key] = obs
            if (latestObservation == null || elapsed >= latestObservation.optLong("elapsed_realtime_ms", -1)) latestObservation = obs
        }
        val cells = mutableListOf<Cell>()
        outer@ for ((sub, obs) in latest) {
            val array = obs.optJSONArray("cells") ?: continue
            val subscription = if (subscriptions == null) null else (0 until subscriptions.length())
                .mapNotNull { subscriptions.optJSONObject(it) }.firstOrNull { text(it, "key") == sub }
            for (i in 0 until array.length()) {
                val row = array.optJSONObject(i) ?: continue
                val radio = text(row, "radio")
                if (!row.optBoolean("registered", false) || radio !in listOf("LTE", "NR")) continue
                if (cells.size >= 8) break@outer
                val id = row.optJSONObject("identity")
                val signal = row.optJSONObject("signal")
                val role = when (row.optString("connection_status")) {
                    "primary" -> "Primary serving"
                    "secondary" -> "Secondary serving"
                    else -> "Registered · role not exposed"
                }
                val carrier = text(id, "operator_alpha_long") ?: text(subscription, "network_operator")
                    ?: text(subscription, "sim_carrier")?.let { "$it (SIM carrier)" } ?: "Carrier not exposed"
                val band = if (id != null && plan != null) runCatching { CellularOverview.bandLabel(radio!!, id, plan) }
                    .getOrDefault("Band not exposed") else "Band not exposed"
                val age = (row.opt("age_ms") as? Number)?.toLong()?.takeIf { it >= 0 }
                    ?.let { "$it ms old at receipt" } ?: "Sample age unavailable at receipt"
                val values = if (radio == "LTE") listOf(
                    metric(signal, "rsrp", "RSRP", "dBm", -160.0..-20.0),
                    metric(signal, "rsrq", "RSRQ", "dB", -50.0..20.0),
                    metric(signal, "rssnr", "SINR", "dB", -30.0..50.0)
                ) else listOf(
                    metric(signal, "ss_rsrp", "SS-RSRP", "dBm", -160.0..-20.0),
                    metric(signal, "ss_rsrq", "SS-RSRQ", "dB", -50.0..30.0),
                    metric(signal, "ss_sinr", "SS-SINR", "dB", -30.0..60.0)
                )
                cells.add(Cell("$radio · $role", carrier, band,
                    text(id, if (radio == "LTE") "earfcn" else "nrarfcn") ?: "Not exposed",
                    text(id, "pci") ?: "Not exposed", age, text(obs, "received_utc"), values))
            }
        }
        val location = latestObservation?.optJSONObject("location")
        val gps = location?.let { LocationEvidence.describeCaptured(it) }
        return Overview(text(latestObservation, "received_utc"), cells, gps)
    }
}
