package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.util.UUID

/** A mobile-only journal of explicitly selected, unchanged phone captures. */
object MobileSurvey {
    const val MAX_POINTS = 20
    const val MAX_BYTES = 16 * 1024 * 1024
    private val idPattern = Regex("[a-zA-Z0-9_-]{1,128}")

    private fun timestamp(value: String): String {
        require(value.length in 1..64) { "Invalid timestamp." }
        try { Instant.parse(value) } catch (_: Exception) { throw IllegalArgumentException("Invalid timestamp.") }
        return value
    }

    private fun name(value: String): String {
        val trimmed = value.trim()
        require(trimmed.isNotEmpty() && trimmed.length <= 80 && trimmed.none { it.isISOControl() }) { "Name must contain 1–80 printable characters." }
        return trimmed
    }

    private fun captureId(capture: JSONObject): String {
        require(capture.optString("format") == "veilbreaker.android.cellular" && capture.optInt("schema_version", -1) == 1) { "Choose a valid phone capture." }
        val id = capture.optString("capture_id")
        require(idPattern.matches(id)) { "Capture ID is invalid." }
        val observations = capture.optJSONArray("observations")
        require(observations != null && observations.length() in 1..4096) { "Capture has no usable observations." }
        require(capture.optJSONObject("collection")?.optString("outcome") in listOf("complete", "partial", "cancelled", "failed")) { "Capture is still collecting or has no final state." }
        return id
    }

    fun create(name: String, now: String): JSONObject = JSONObject()
        .put("format", "veilbreaker.mobile.survey").put("schema_version", 1)
        .put("survey_id", UUID.randomUUID().toString()).put("name", name(name))
        .put("created_utc", timestamp(now)).put("lifecycle", "open").put("points", JSONArray())

    fun validate(survey: JSONObject): JSONObject {
        require(survey.optString("format") == "veilbreaker.mobile.survey" && survey.optInt("schema_version", -1) == 1) { "Unsupported mobile survey." }
        require(Regex("[a-f0-9-]{36}").matches(survey.optString("survey_id"))) { "Invalid survey ID." }
        name(survey.optString("name")); timestamp(survey.optString("created_utc"))
        require(survey.optString("lifecycle") in listOf("open", "completed")) { "Invalid survey state." }
        val points = survey.optJSONArray("points") ?: throw IllegalArgumentException("Invalid survey points.")
        require(points.length() <= MAX_POINTS) { "Survey has too many points." }
        val ids = HashSet<String>()
        for (i in 0 until points.length()) {
            val point = points.optJSONObject(i) ?: throw IllegalArgumentException("Invalid survey point.")
            timestamp(point.optString("attached_utc"))
            val capture = point.optJSONObject("capture") ?: throw IllegalArgumentException("Capture is missing.")
            require(ids.add(captureId(capture))) { "Duplicate capture in survey." }
        }
        if (survey.optString("lifecycle") == "completed") timestamp(survey.optString("completed_utc"))
        require(survey.toString().toByteArray(Charsets.UTF_8).size <= MAX_BYTES) { "Survey exceeds 16 MiB." }
        return survey
    }

    fun addCapture(survey: JSONObject, capture: JSONObject, now: String): JSONObject {
        validate(survey)
        require(survey.getString("lifecycle") == "open") { "Reopen the survey before adding captures." }
        val id = captureId(capture); val points = survey.getJSONArray("points")
        require(points.length() < MAX_POINTS) { "A mobile survey can contain up to 20 captures." }
        require((0 until points.length()).none { points.getJSONObject(it).getJSONObject("capture").getString("capture_id") == id }) { "This capture is already in the survey." }
        val copy = JSONObject(survey.toString())
        copy.getJSONArray("points").put(JSONObject().put("attached_utc", timestamp(now)).put("capture", JSONObject(capture.toString())))
        return validate(copy)
    }

    /** A direct capture can attach only a completed or partial result, never a cancellation or failure. */
    fun addNewCapture(survey: JSONObject, capture: JSONObject, now: String): JSONObject {
        val outcome = capture.optJSONObject("collection")?.optString("outcome")
        require(outcome == "complete" || outcome == "partial") { "No completed or partial capture was collected; survey is unchanged." }
        return addCapture(survey, capture, now)
    }

    /** An operator observation belongs to the survey point, never the original capture. */
    fun setPointNote(survey: JSONObject, captureId: String, note: String): JSONObject {
        validate(survey)
        require(survey.getString("lifecycle") == "open") { "Reopen the survey before editing point notes." }
        val value = note.trim()
        require(value.length <= 500 && value.none { it.isISOControl() && it != '\n' }) { "Note must contain at most 500 printable characters." }
        val copy = JSONObject(survey.toString())
        val points = copy.getJSONArray("points")
        val point = (0 until points.length()).asSequence().map { points.getJSONObject(it) }
            .firstOrNull { it.getJSONObject("capture").optString("capture_id") == captureId }
            ?: throw IllegalArgumentException("Survey point is unavailable.")
        if (value.isEmpty()) point.remove("operator_note") else point.put("operator_note", value)
        return validate(copy)
    }

    fun complete(survey: JSONObject, now: String): JSONObject {
        validate(survey); require(survey.getString("lifecycle") == "open") { "Survey is already complete." }
        return validate(JSONObject(survey.toString()).put("lifecycle", "completed").put("completed_utc", timestamp(now)))
    }

    fun reopen(survey: JSONObject): JSONObject {
        validate(survey); require(survey.getString("lifecycle") == "completed") { "Survey is already open." }
        return JSONObject(survey.toString()).put("lifecycle", "open").apply { remove("completed_utc") }
    }

    /** Readable snapshot summary; missing metrics stay unavailable. */
    fun signalSummary(capture: JSONObject): String {
        val observations = capture.optJSONArray("observations") ?: return "No cellular observation."
        val last = observations.optJSONObject(observations.length() - 1) ?: return "No cellular observation."
        val cells = last.optJSONArray("cells") ?: return "No registered LTE or NR cell in the last observation."
        val result = mutableListOf<String>()
        for (i in 0 until cells.length()) {
            val cell = cells.optJSONObject(i) ?: continue
            val radio = cell.optString("radio")
            if (!cell.optBoolean("registered") || radio !in listOf("LTE", "NR")) continue
            val signal = cell.optJSONObject("signal")
            fun measure(key: String, unit: String): String {
                val q = signal?.optJSONObject(key) ?: return "not exposed"
                val value = q.opt("value") as? Number ?: return "not exposed"
                return if (q.optString("unit") == unit && value.toDouble().isFinite()) "$value $unit" else "not exposed"
            }
            val rsrp = measure(if (radio == "NR") "ss_rsrp" else "rsrp", "dBm")
            val sinr = measure(if (radio == "NR") "ss_sinr" else "rssnr", "dB")
            result.add("$radio · RSRP $rsrp · SINR $sinr")
            if (result.size == 4) break
        }
        return result.joinToString("\n").ifEmpty { "No registered LTE or NR cell in the last observation." }
    }
}
