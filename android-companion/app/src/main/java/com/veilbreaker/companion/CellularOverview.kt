package com.veilbreaker.companion

import org.json.JSONObject

/** Presentation only: preserve raw modem bands, channel numbers and cell roles. */
object CellularOverview {
    private fun value(obj: JSONObject, key: String): String =
        if (!obj.has(key) || obj.isNull(key)) "Not exposed" else obj.get(key).toString()

    fun bandLabel(radio: String, identity: JSONObject, plan: JSONObject): String {
        val reported = identity.optJSONArray("bands")
        val numbers = sortedSetOf<Int>()
        if (reported != null) for (i in 0 until reported.length()) numbers.add(reported.getInt(i))
        val modem = numbers.isNotEmpty()
        val channelKey = if (radio == "LTE") "earfcn" else "nrarfcn"
        if (!modem && radio in listOf("LTE", "NR") && identity.has(channelKey) && !identity.isNull(channelKey)) {
            val channel = identity.optLong(channelKey, -1)
            val ranges = plan.getJSONArray("ranges")
            for (i in 0 until ranges.length()) {
                val range = ranges.getJSONObject(i)
                if (range.getString("radio") == radio && channel >= range.getLong("min") && channel <= range.getLong("max")) numbers.add(range.getInt("band"))
            }
        }
        if (numbers.isEmpty()) return "Band not exposed"
        return numbers.joinToString(", ") { (if (radio == "NR") "n" else "B") + it } +
            if (modem) " (modem reported)" else " (channel-derived candidates)"
    }

    private fun role(cell: JSONObject): String {
        val connection = cell.optString("connection_status")
        if (cell.optBoolean("registered", false)) return when (connection) {
            "primary" -> "Primary serving"
            "secondary" -> "Secondary serving"
            else -> "Registered; role not exposed"
        }
        if (connection in listOf("primary", "secondary")) return "Conflicting serving flags"
        return if (cell.has("registered") && !cell.isNull("registered")) "Neighbor" else "Role not exposed"
    }

    fun render(envelope: JSONObject, plan: JSONObject): String {
        val observations = envelope.getJSONArray("observations")
        val latest = linkedMapOf<String, JSONObject>()
        for (i in 0 until observations.length()) {
            val obs = observations.getJSONObject(i); val sub = obs.getString("subscription_key")
            if (!latest.containsKey(sub) || obs.getLong("elapsed_realtime_ms") >= latest.getValue(sub).getLong("elapsed_realtime_ms")) latest[sub] = obs
        }
        val lines = mutableListOf("Latest reported connection", "Captured state, not an exhaustive band scan.")
        var connected = 0
        fun describe(cell: JSONObject, obs: JSONObject): String {
            val identity = cell.getJSONObject("identity"); val radio = cell.getString("radio")
            var carrier = value(identity,"operator_alpha_long")
            if (carrier == "Not exposed" && cell.optBoolean("registered",false)) {
                val subscriptions = envelope.optJSONArray("subscriptions")
                if (subscriptions != null) for (i in 0 until subscriptions.length()) {
                    val sub = subscriptions.getJSONObject(i)
                    if (sub.optString("key") == obs.getString("subscription_key")) carrier = value(sub,"network_operator")
                }
            }
            val signal = cell.getJSONObject("signal")
            val measures = signal.keys().asSequence().sorted().mapNotNull { key ->
                val q = signal.optJSONObject(key)
                if (q == null || q.isNull("value") || !q.has("value")) null else "${key.uppercase().replace('_','-')}: ${q.get("value")} ${q.optString("unit")}" }
            val age = if (cell.isNull("age_ms") || !cell.has("age_ms")) "unknown sample age" else
                "${cell.getLong("age_ms")} ms old" + if (cell.getLong("age_ms") > 10000) " (old sample)" else ""
            val channel = value(identity, if (radio == "LTE") "earfcn" else "nrarfcn")
            return "${obs.getString("subscription_key")} / ${role(cell)} / $radio ${bandLabel(radio,identity,plan)}\n" +
                "Carrier $carrier | MCC/MNC ${value(identity,"mcc")}/${value(identity,"mnc")}\n" +
                "Cell ${value(identity,"cell_id")} | PCI ${value(identity,"pci")} | channel $channel\n" +
                measures.joinToString(" | ").ifEmpty { "Signal not exposed" } + "\n${obs.getString("received_utc")} | $age"
        }
        for ((sub, obs) in latest) {
            lines.add("$sub latest observation: ${obs.getString("received_utc")}")
            val cells = obs.getJSONArray("cells")
            for (i in 0 until cells.length()) {
                val cell = cells.getJSONObject(i)
                if (cell.optBoolean("registered",false)) { lines.add(describe(cell,obs)); connected++ }
            }
        }
        if (connected == 0) lines.add("No connected cells reported in latest observation")
        val neighbors = linkedMapOf<String, String>()
        val bands = linkedMapOf<String, MutableSet<String>>()
        var omitted = 0
        val chronological = (0 until observations.length()).map { observations.getJSONObject(it) }.sortedBy { it.getLong("elapsed_realtime_ms") }
        for (obs in chronological) {
            val sub = obs.getString("subscription_key")
            val cells = obs.getJSONArray("cells"); val current = latest[sub] === obs
            for (j in 0 until cells.length()) {
                val cell = cells.getJSONObject(j); val identity = cell.getJSONObject("identity")
                val band = bandLabel(cell.getString("radio"), identity, plan)
                val whenSeen = if (current) "latest observation" else "earlier observation"
                if (band != "Band not exposed") {
                    val key = "$sub / ${cell.getString("radio")} $band"
                    bands.getOrPut(key) { linkedSetOf() }.add("${role(cell)} / $whenSeen")
                }
                if (!cell.optBoolean("registered",false)) {
                    val key = sub + cell.getString("radio") + identity.toString() + role(cell)
                    if (neighbors.containsKey(key) || neighbors.size < 1024) neighbors[key] = describe(cell,obs) + " | $whenSeen"
                    else omitted++
                }
            }
        }
        lines.add("\nNeighbor / unclassified observations")
        if (neighbors.isEmpty()) lines.add("No neighbors reported") else lines.addAll(neighbors.values)
        lines.add("\nBands observed during capture")
        if (bands.isEmpty()) lines.add("No band labels available")
        for ((band, roles) in bands) lines.add(band + "\n" + roles.joinToString("; "))
        if (omitted > 0) lines.add("$omitted entries omitted from preview (1024 groups maximum); raw capture retained.")
        lines.add("Channel-derived candidates are not confirmed bands or carriers. Android can omit neighbors, bands and signal fields.")
        return lines.joinToString("\n\n")
    }
}
