package com.veilbreaker.companion

import org.json.JSONObject
import java.util.Locale

/** Read-only, per-point presentation; no aggregation, inferred identity or signal estimate. */
object SurveyComparisonModel {
    data class Point(
        val number: Int, val captureId: String, val createdUtc: String, val outcome: String,
        val location: String, val servingCells: List<CellInventoryModel.Cell>,
        val omittedServing: Int, val inventoryIncomplete: Boolean, val operatorNote: String?
    )

    fun build(survey: JSONObject, plan: JSONObject?): List<Point> {
        MobileSurvey.validate(survey)
        val points = survey.getJSONArray("points")
        return (0 until points.length()).map { index ->
            val point = points.getJSONObject(index)
            val capture = point.getJSONObject("capture")
            val inventory = CellInventoryModel.build(capture, plan)
            val serving = inventory.cells.filter { it.group == CellInventoryModel.Group.SERVING }
            Point(index + 1, capture.getString("capture_id"),
                capture.optString("created_utc").ifBlank { "Capture time not exposed" },
                capture.getJSONObject("collection").optString("outcome", "unknown"),
                location(capture), serving.take(4), (serving.size - 4).coerceAtLeast(0), inventory.omitted > 0,
                (point.opt("operator_note") as? String)?.takeIf { it.isNotBlank() && it.length <= 500 && it.none { ch -> ch.isISOControl() && ch != '\n' } })
        }
    }

    private fun location(capture: JSONObject): String {
        val observations = capture.optJSONArray("observations") ?: return "No valid reported location"
        for (i in (minOf(observations.length(), 4096) - 1) downTo 0) {
            val observation = observations.optJSONObject(i) ?: continue
            val location = observation.optJSONObject("location") ?: continue
            val fix = GpsSpatialModel.fix(location) ?: continue
            val source = location.optString("source").takeIf { it in setOf("phone", "external_receiver", "imported") } ?: "source not exposed"
            val provider = fix.provider?.take(120) ?: "provider not exposed"
            val age = fix.ageAtReceiptMs?.let { "$it ms old at receipt" } ?: "age not exposed"
            val accuracy = String.format(Locale.US, "%.1f", fix.accuracy)
            return "Last valid reported location · $source · $provider · ±$accuracy m · $age · ${fix.mockLabel()}"
        }
        return "No valid reported location"
    }
}
