package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.util.UUID

object CaptureSerializer {
    fun quantity(value: Int, unit: String, min: Int, max: Int): JSONObject =
        JSONObject().put("unit", unit).apply {
            if (value == Int.MAX_VALUE || value !in min..max) {
                put("value", JSONObject.NULL); put("reason", "not_reported")
            } else put("value", value)
        }

    fun age(receivedElapsedMs: Long, modemElapsedMs: Long): Long? =
        if (modemElapsedMs <= 0 || modemElapsedMs > receivedElapsedMs) null else receivedElapsedMs - modemElapsedMs

    fun envelope(manufacturer: String, model: String, androidVersion: String, api: Int,
                 version: String, cells: List<JSONObject>, elapsed: Long, outcome: String,
                 notes: List<String>, startedUtc: String = Instant.now().toString()): JSONObject {
        val receipt = Instant.now().toString()
        return JSONObject().put("format", "veilbreaker.android.cellular").put("schema_version", 1)
            .put("capture_id", UUID.randomUUID().toString()).put("created_utc", receipt)
            .put("device", JSONObject().put("manufacturer", manufacturer).put("model", model)
                .put("android_version", androidVersion).put("api_level", api).put("companion_version", version))
            .put("collection", JSONObject().put("mode", "snapshot").put("started_utc", startedUtc)
                .put("ended_utc", receipt).put("outcome", outcome).put("permissions", JSONObject())
                .put("notes", JSONArray(notes)))
            .put("subscriptions", JSONArray().put(JSONObject().put("key", "selected-sim")))
            .put("observations", JSONArray().put(JSONObject().put("observation_id", "snapshot-1")
                .put("subscription_key", "selected-sim").put("received_utc", receipt)
                .put("elapsed_realtime_ms", elapsed).put("outcome", outcome).put("cells", JSONArray(cells))))
    }
}
