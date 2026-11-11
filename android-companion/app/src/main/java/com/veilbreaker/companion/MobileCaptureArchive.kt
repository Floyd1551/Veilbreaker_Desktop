package com.veilbreaker.companion

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant

/** A separate operator-managed journal of unchanged copies; never the current capture. */
object MobileCaptureArchive {
    const val ID = "00000000-0000-0000-0000-000000000001"
    fun empty(now: String): JSONObject = MobileSurvey.validate(MobileSurvey.create("Capture archive", now).put("survey_id", ID))
    private fun validate(archive: JSONObject): JSONObject {
        MobileSurvey.validate(archive)
        require(archive.optString("survey_id") == ID && archive.optString("lifecycle") == "open") { "Invalid capture archive." }
        return archive
    }
    fun captures(archive: JSONObject): List<JSONObject> {
        val points = validate(archive).getJSONArray("points")
        return (0 until points.length()).map { JSONObject(points.getJSONObject(it).getJSONObject("capture").toString()) }
    }
    fun add(archive: JSONObject, capture: JSONObject, now: String): JSONObject {
        val points = validate(archive).getJSONArray("points")
        val id = capture.optString("capture_id")
        require((0 until points.length()).none { points.getJSONObject(it).getJSONObject("capture").optString("capture_id") == id }) {
            "This capture is already archived."
        }
        require(points.length() < MobileSurvey.MAX_POINTS) { "The archive holds up to 20 captures. Export or delete a copy before adding another." }
        return MobileSurvey.addCapture(archive, capture, now)
    }
    fun remove(archive: JSONObject, captureId: String): JSONObject {
        val copy = JSONObject(validate(archive).toString()); val points = copy.getJSONArray("points")
        val kept = JSONArray(); var removed = false
        for (index in 0 until points.length()) {
            val point = points.getJSONObject(index)
            if (point.getJSONObject("capture").getString("capture_id") == captureId) removed = true else kept.put(point)
        }
        require(removed) { "Capture no longer exists in the archive." }
        copy.put("points", kept)
        return validate(copy)
    }
}

class MobileCaptureArchiveStore(context: Context) {
    private val store = MobileSurveyStore(context, archive = true)
    private fun loadOrEmpty(): JSONObject = if (store.exists(MobileCaptureArchive.ID)) store.load(MobileCaptureArchive.ID)
        else MobileCaptureArchive.empty(Instant.now().toString())
    fun list(): List<JSONObject> = MobileSurveyTransactions.locked { MobileCaptureArchive.captures(loadOrEmpty()) }
    fun add(capture: JSONObject): List<JSONObject> = MobileSurveyTransactions.locked {
        val updated = MobileCaptureArchive.add(loadOrEmpty(), capture, Instant.now().toString())
        store.save(updated); MobileCaptureArchive.captures(updated)
    }
    fun remove(id: String): List<JSONObject> = MobileSurveyTransactions.locked {
        require(store.exists(MobileCaptureArchive.ID)) { "Capture archive is unavailable." }
        val updated = MobileCaptureArchive.remove(store.load(MobileCaptureArchive.ID), id)
        store.save(updated); MobileCaptureArchive.captures(updated)
    }
}
