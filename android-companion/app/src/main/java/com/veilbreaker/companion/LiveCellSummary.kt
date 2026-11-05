package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject

/** Format one transient public Android cell response without altering saved evidence. */
object LiveCellSummary {
    private const val DISPLAY_LIMIT = 10
    fun render(cells: List<JSONObject>, plan: JSONObject): String {
        if (cells.isEmpty()) return "No cells reported. Android or the modem may omit information."
        val observation = JSONObject().put("subscription_key", "selected-sim")
            .put("elapsed_realtime_ms", 1).put("cells", JSONArray(cells))
        val container = JSONObject().put("observations", JSONArray().put(observation))
        val inventory = CellInventoryModel.build(container, plan)
        val displayed = inventory.cells.take(DISPLAY_LIMIT)
        if (displayed.isEmpty()) return "No readable cells reported. Android or the modem may omit information."
        val blocks = displayed.map { cell ->
            val identity = cell.identity.take(8)
            listOfNotNull("${cell.radio} · ${cell.role} · ${cell.band}", cell.carrier,
                identity.takeIf { it.isNotEmpty() }?.joinToString(" · "),
                cell.metrics.take(12).joinToString(" · "), cell.age).joinToString("\n")
        }.toMutableList()
        val omitted = (inventory.total - displayed.size).coerceAtLeast(0)
        if (omitted > 0) blocks.add("$omitted more cell reports not shown in this live view.")
        return blocks.joinToString("\n\n")
    }
}
