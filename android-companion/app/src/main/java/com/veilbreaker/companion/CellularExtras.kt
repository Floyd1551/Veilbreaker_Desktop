package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject

/** Helpers for optional public telephony fields; do not convert missing sentinels into measurements. */
object CellularExtras {
    fun identityInteger(identity: JSONObject, name: String, value: Int) {
        identity.put(name, if (value == Int.MAX_VALUE || value < 0) JSONObject.NULL else value)
    }
    fun cellId(identity: JSONObject, value: Int) {
        identity.put("cell_id", if (value == Int.MAX_VALUE || value < 0) JSONObject.NULL else value.toString())
    }
    fun nrCqiReport(details: JSONObject, values: List<Int?>) {
        if (values.isEmpty()) return
        details.put("nr_csi_cqi_report", JSONArray().apply {
            values.take(64).forEach { put(if (it != null && it in 0..15) it else JSONObject.NULL) }
        })
        if (values.size > 64) details.put("nr_csi_cqi_truncated", true)
    }
}
