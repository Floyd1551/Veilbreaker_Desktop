package com.veilbreaker.companion

import org.json.JSONObject

/** Foreground-only observations of changes in an Android-reported serving identity.
 * An event is not proof of a handover, physical tower, or its cause. */
class ServingCellChangeTracker(private val subscriptionKey: String) {
    data class Identity(val radio: String, val mcc: String, val mnc: String,
                        val cellId: String, val pci: Int, val channel: Int)
    data class Event(val previous: Identity, val current: Identity, val receivedElapsedMs: Long,
                     val receivedUtc: String?, val sampleElapsedMs: Long, val ageAtReceiptMs: Long,
                     val previousRole: String, val currentRole: String,
                     val source: String = "Android cell-info response")
    private data class Sample(val identity: Identity, val elapsed: Long, val received: Long, val role: String)
    private val history = mutableListOf<Event>()
    private var baseline: Sample? = null
    private var lastReceipt: Long? = null
    val events: List<Event> get() = history.toList()
    var status: String = "Waiting for an identifiable recent serving-cell response."
        private set

    init { require(subscriptionKey.isNotBlank() && subscriptionKey.length <= 160) }

    fun reset() {
        history.clear(); baseline = null; lastReceipt = null
        status = "Waiting for an identifiable recent serving-cell response."
    }

    /** Process only the selected subscription; responses are never stored as captured evidence. */
    fun accept(subscriptionKey: String, cells: List<JSONObject>, receivedElapsedMs: Long, receivedUtc: String?) {
        if (subscriptionKey != this.subscriptionKey) return
        fun breakContinuity(message: String) { baseline = null; status = message }
        if (receivedElapsedMs < 0) { breakContinuity("Response time unavailable; continuity paused."); return }
        if (lastReceipt != null && receivedElapsedMs <= lastReceipt!!) {
            breakContinuity("Out-of-order response time; continuity paused."); return
        }
        lastReceipt = receivedElapsedMs
        if (cells.size > MAX_CELLS) { breakContinuity("Cell response exceeds review limit; continuity paused."); return }
        val registered = cells.filter { it.opt("registered") == true }
        val primary = registered.filter { it.optString("connection_status") == "primary" }
        val row = when {
            primary.size == 1 -> primary.single()
            primary.isNotEmpty() -> null
            registered.size == 1 && registered.single().optString("connection_status") in listOf("", "none", "unknown") -> registered.single()
            else -> null
        }
        if (row == null) { breakContinuity("No unambiguous primary or sole registered cell; continuity paused."); return }
        val radio = row.optString("radio")
        val id = row.optJSONObject("identity")
        fun text(key: String): String? = id?.opt(key)?.let { if (it == JSONObject.NULL) null else it.toString() }
        fun number(value: Any?): Long? = try {
            (value as? Number)?.toString()?.toBigDecimal()?.longValueExact()
        } catch (_: NumberFormatException) { null } catch (_: ArithmeticException) { null }
        val mcc = text("mcc")?.takeIf { it.matches(Regex("[0-9]{3}")) && it.toInt() >= 100 }
        val mnc = text("mnc")?.takeIf { it.matches(Regex("[0-9]{2,3}")) }
        val maxCell = when (radio) { "LTE" -> 268435455L; "NR" -> 68719476735L; else -> -1L }
        val cell = text("cell_id")?.takeIf { it.matches(Regex("[0-9]{1,16}")) }?.toLongOrNull()?.takeIf { it in 0..maxCell }
        val maxPci = when (radio) { "LTE" -> 503L; "NR" -> 1007L; else -> -1L }
        val pci = number(id?.opt("pci"))?.takeIf { it in 0..maxPci }
        val channel = number(id?.opt(if (radio == "LTE") "earfcn" else "nrarfcn"))
            ?.takeIf { it in 0..(if (radio == "LTE") 262143L else 3279165L) }
        val age = number(row.opt("age_ms"))?.takeIf { it in 0..MAX_AGE_MS && it <= receivedElapsedMs }
        if (mcc == null || mnc == null || cell == null || pci == null || channel == null || age == null) {
            breakContinuity("Identity or recent modem timestamp unavailable; continuity paused."); return
        }
        val role = if (primary.size == 1) "primary" else "registered_role_unconfirmed"
        val next = Sample(Identity(radio, mcc, mnc, cell.toString(), pci.toInt(), channel.toInt()), receivedElapsedMs - age, receivedElapsedMs, role)
        val previous = baseline
        if (previous != null && (next.received < previous.received || next.elapsed < previous.elapsed)) {
            breakContinuity("Older response or modem timestamp; continuity paused."); return
        }
        if (previous != null && next.elapsed == previous.elapsed) {
            if (next.identity != previous.identity) breakContinuity("Conflicting identities for one modem timestamp; continuity paused.")
            else status = "Repeated modem timestamp; no new event."
            return
        }
        if (previous != null && next.elapsed - previous.elapsed > MAX_GAP_MS) {
            baseline = next; status = "Long observation gap; comparison restarted."; return
        }
        if (previous != null && previous.identity != next.identity) {
            val utc = receivedUtc?.trim()?.takeIf { it.isNotEmpty() && it.length <= 80 && '\n' !in it && '\r' !in it }
            history.add(Event(previous.identity, next.identity, receivedElapsedMs, utc, next.elapsed, age, previous.role, next.role))
            if (history.size > LIMIT) history.removeAt(0)
            status = "Reported cell identity changed; serving role, physical site and cause may be unconfirmed."
        } else status = if (role == "primary") "Tracking a recent primary serving identity."
                        else "Tracking one registered identity; primary role is not confirmed."
        baseline = next
    }

    private companion object { const val LIMIT = 50; const val MAX_CELLS = 256; const val MAX_AGE_MS = 20_000L; const val MAX_GAP_MS = 45_000L }
}
