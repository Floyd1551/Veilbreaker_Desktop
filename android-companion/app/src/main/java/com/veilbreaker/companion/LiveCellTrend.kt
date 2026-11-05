package com.veilbreaker.companion

import org.json.JSONObject

/** A bounded, ephemeral trend of distinct recent modem timestamps for one identified serving cell. */
class LiveCellTrend {
    data class Point(val modemElapsedMs: Long, val value: Double, val ageAtReceiptMs: Long)
    private data class Key(val radio: String, val mcc: String, val mnc: String, val cell: String, val pci: Int, val channel: Int)
    private var identity: Key? = null
    private val samples = mutableListOf<Point>()
    val points: List<Point> get() = samples.toList()
    var status: String = "Waiting for an identifiable serving-cell measurement."
        private set
    var metric: String = ""
        private set
    var cellLabel: String = ""
        private set

    fun reset(message: String = "Waiting for an identifiable serving-cell measurement.") {
        samples.clear(); identity = null; metric = ""; cellLabel = ""; status = message
    }

    /** Each call represents one cell-info response received at [receivedElapsedMs]. */
    fun accept(cells: List<JSONObject>, receivedElapsedMs: Long) {
        val registered = cells.filter { it.opt("registered") == true }
        val primary = registered.filter { it.optString("connection_status") == "primary" }
        val row = when {
            primary.size == 1 -> primary.single()
            primary.isNotEmpty() -> null
            registered.size == 1 -> registered.single()
            else -> null
        }
        if (row == null) { reset("No unambiguous serving cell in this response; history cleared."); return }
        val radio = row.optString("radio")
        val metricKey = when (radio) { "LTE" -> "rsrp"; "NR" -> "ss_rsrp"; else -> null }
        val id = row.optJSONObject("identity")
        fun text(field: String) = id?.opt(field)?.let { if (it == JSONObject.NULL) null else it.toString() }
        val mcc = text("mcc")?.takeIf { it.matches(Regex("[0-9]{3}")) }
        val mnc = text("mnc")?.takeIf { it.matches(Regex("[0-9]{2,3}")) }
        val cell = text("cell_id")?.takeIf { it.matches(Regex("[0-9]{1,16}")) }
        val pci = (id?.opt("pci") as? Number)?.toInt()?.takeIf { it >= 0 && it < Int.MAX_VALUE }
        val channel = (id?.opt(if (radio == "LTE") "earfcn" else "nrarfcn") as? Number)?.toInt()?.takeIf { it >= 0 && it < Int.MAX_VALUE }
        if (metricKey == null || mcc == null || mnc == null || cell == null || pci == null || channel == null) {
            reset("Cell identity or LTE/NR channel unavailable; history cleared to avoid mixing cells."); return
        }
        val key = Key(radio, mcc, mnc, cell, pci, channel)
        val age = (row.opt("age_ms") as? Number)?.toLong()
        val measurement = row.optJSONObject("signal")?.optJSONObject(metricKey)
        val value = (measurement?.opt("value") as? Number)?.toDouble()
        if (age == null || age < 0 || age > MAX_AGE_MS || receivedElapsedMs <= age ||
            measurement?.optString("unit") != "dBm" || value == null || !value.isFinite() || value !in -160.0..-20.0) {
            reset("Measurement or recent modem timestamp unavailable; history cleared."); return
        }
        val timestamp = receivedElapsedMs - age
        val changed = identity != null && identity != key
        if (changed) { samples.clear(); identity = null }
        val previous = samples.lastOrNull()
        if (previous != null && timestamp == previous.modemElapsedMs) {
            if (previous.value != value) { reset("Conflicting values for the same modem timestamp; history cleared."); return }
            status = "Repeated modem timestamp; no new point added. Age at receipt ${age} ms."
            return
        }
        if (previous != null && timestamp < previous.modemElapsedMs) {
            reset("Older modem timestamp returned; history cleared."); return
        }
        val gap = previous != null && timestamp - previous.modemElapsedMs > MAX_GAP_MS
        if (gap) samples.clear()
        identity = key
        metric = if (radio == "LTE") "RSRP" else "SS-RSRP"
        cellLabel = "$radio · cell $cell · PCI $pci · ${if (radio == "LTE") "EARFCN" else "NR-ARFCN"} $channel"
        samples.add(Point(timestamp, value, age)); if (samples.size > LIMIT) samples.removeAt(0)
        val role = if (row.optString("connection_status") == "primary") "Primary serving" else "Registered; primary role not confirmed"
        status = "$role · $metric ${value.toInt()} dBm · age at receipt ${age} ms" +
            if (changed || gap) " · history restarted after cell change or gap." else "."
    }

    private companion object { const val LIMIT = 30; const val MAX_AGE_MS = 20_000L; const val MAX_GAP_MS = 45_000L }
}
