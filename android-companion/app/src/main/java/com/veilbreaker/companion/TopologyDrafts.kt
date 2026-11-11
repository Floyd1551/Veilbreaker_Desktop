package com.veilbreaker.companion

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject

/** A bounded operator sketch, never network discovery or measured connectivity. */
object TopologyDraftCodec {
    private const val FORMAT = "veilbreaker.android.topology_draft"
    private const val MAX_LENGTH = 16384

    private fun validate(state: TopologyEditor.State): TopologyEditor.State? {
        var checked = TopologyEditor.State()
        for (name in state.nodes) {
            val next = TopologyEditor.addNode(checked, name) ?: return null
            if (next.nodes.last() != name) return null
            checked = next
        }
        for ((a, b) in state.links) checked = TopologyEditor.addLink(checked, a, b) ?: return null
        return checked
    }

    fun encode(state: TopologyEditor.State): String? {
        val checked = validate(state) ?: return null
        val links = JSONArray()
        checked.links.forEach { (a, b) -> links.put(JSONArray().put(a).put(b)) }
        return JSONObject().put("format", FORMAT).put("schema_version", 1)
            .put("provenance", "operator_entered").put("nodes", JSONArray(checked.nodes)).put("links", links).toString()
    }

    fun decode(encoded: String?): TopologyEditor.State? {
        if (encoded == null || encoded.length > MAX_LENGTH) return null
        return try {
            val record = JSONObject(encoded)
            if (record.opt("format") != FORMAT || record.opt("schema_version") != 1 || record.opt("provenance") != "operator_entered") return null
            val nodes = record.optJSONArray("nodes") ?: return null
            val links = record.optJSONArray("links") ?: return null
            if (nodes.length() > 12 || links.length() > 30) return null
            val names = (0 until nodes.length()).map { nodes.opt(it) as? String ?: return null }
            val edges = (0 until links.length()).map { index ->
                val pair = links.optJSONArray(index) ?: return null
                if (pair.length() != 2) return null
                val a = pair.opt(0) as? Int ?: return null
                val b = pair.opt(1) as? Int ?: return null
                a to b
            }
            validate(TopologyEditor.State(names, edges))
        } catch (_: Exception) { null }
    }
}

class TopologyDraftStore(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences("planning_drafts", Context.MODE_PRIVATE)
    fun exists(): Boolean = preferences.contains("topology")
    fun load(): TopologyEditor.State? = try { TopologyDraftCodec.decode(preferences.getString("topology", null)) } catch (_: ClassCastException) { null }
    fun save(state: TopologyEditor.State): Boolean {
        val encoded = TopologyDraftCodec.encode(state) ?: return false
        return preferences.edit().putString("topology", encoded).commit()
    }
    fun clear(): Boolean = preferences.edit().remove("topology").commit()
}
