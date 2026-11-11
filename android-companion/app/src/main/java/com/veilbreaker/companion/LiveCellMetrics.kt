package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject

/** Display an unambiguous reported cell without treating this transient response as saved evidence. */
object LiveCellMetrics {
    fun build(cells: List<JSONObject>, plan: JSONObject): LiveOverviewModel.Cell? {
        val registered = cells.filter { it.opt("registered") == true }
        val primary = registered.filter { it.optString("connection_status") == "primary" }
        val selected = when {
            primary.size == 1 -> primary.single()
            primary.isNotEmpty() -> return null
            registered.size == 1 -> registered.single()
            else -> return null
        }
        if (selected.optString("radio") !in setOf("LTE", "NR")) return null
        val observation = JSONObject().put("subscription_key", "selected-sim").put("elapsed_realtime_ms", 1)
            .put("cells", JSONArray().put(selected))
        val envelope = JSONObject().put("observations", JSONArray().put(observation))
        return LiveOverviewModel.build(envelope, plan).cells.singleOrNull()
    }
}
