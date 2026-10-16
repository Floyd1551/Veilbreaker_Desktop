package com.veilbreaker.companion

import org.json.JSONObject
import org.json.JSONArray
import java.security.MessageDigest
import java.time.Instant
import java.util.UUID

/** Main-thread state machine; endpoint must dispatch commands to the activity thread. */
class UsbSession(private val now: () -> Long, private val sample: () -> Unit,
                 private val save: (JSONObject) -> Unit) {
    val token = UUID.randomUUID().toString().replace("-", "")
    val id = UUID.randomUUID().toString()
    private var state = "armed"
    private var deadline = 0L
    private var nextSample = 0L
    private var pending = false
    private var capture: JSONObject? = null
    private val used = mutableSetOf<String>()
    private var started = ""

    fun command(name: String, suppliedToken: String, body: JSONObject): JSONObject {
        require(MessageDigest.isEqual(token.toByteArray(), suppliedToken.toByteArray())) { "Authorization required" }
        val request = body.getString("request_id")
        require(request.length in 1..64 && used.size < 4096 && used.add(request)) { "Invalid request identifier" }
        if (name != "start") require(body.optString("session_id") == id) { "Session mismatch" }
        expire()
        when (name) {
            "start" -> {
                require(state == "armed") { "Arm a new session on the phone" }
                val duration = body.getInt("duration_s")
                require(duration in 5..300) { "Duration must be 5 to 300 seconds" }
                state = "collecting"; started = Instant.now().toString(); deadline = now() + duration * 1000
            }
            "sample" -> {
                require(state != "armed") { "Start session first" }
                if (state == "collecting" && !pending && now() >= nextSample) {
                    pending = true; nextSample = now() + 5000; sample()
                }
            }
            "stop" -> finish(if (body.optString("outcome") == "complete") "complete" else "cancelled")
            "status" -> Unit
            else -> throw IllegalArgumentException("Unknown command")
        }
        return JSONObject().put("protocol", 1).put("request_id", request).put("session_id", id)
            .put("status", state).put("pending", pending).apply { capture?.let { put("capture", JSONObject(it.toString())) } }
    }

    fun accept(snapshot: JSONObject) {
        if (state != "collecting" || !pending) return
        pending = false
        if (capture == null) {
            capture = JSONObject(snapshot.toString()).put("capture_id", id).put("observations", JSONArray())
            capture!!.getJSONObject("collection").put("mode", "session").put("started_utc", started)
                .put("notes", JSONArray().put("Foreground USB session. Modem samples may be cached; receipt times are not modem sample times."))
        }
        val result = capture!!
        val observations = result.getJSONArray("observations")
        val observation = JSONObject(snapshot.getJSONArray("observations").getJSONObject(0).toString())
        observation.put("observation_id", "sample-" + (observations.length() + 1)); observations.put(observation)
        result.getJSONObject("collection").put("ended_utc", observation.getString("received_utc")).put("outcome", "partial")
        save(JSONObject(result.toString()))
        expire()
    }

    fun terminal() = state !in listOf("armed", "collecting")

    fun expire() { if (state == "collecting" && now() >= deadline) finish("complete") }

    fun finish(outcome: String) {
        if (state !in listOf("armed", "collecting")) return
        val observations = capture?.getJSONArray("observations")
        state = if (outcome == "complete" && (pending || observations == null || (0 until observations.length()).any { observations.getJSONObject(it).optString("outcome") != "complete" })) "partial" else outcome
        pending = false
        capture?.let {
            it.getJSONObject("collection").put("outcome", state).put("ended_utc", Instant.now().toString())
            save(JSONObject(it.toString()))
        }
    }
}
