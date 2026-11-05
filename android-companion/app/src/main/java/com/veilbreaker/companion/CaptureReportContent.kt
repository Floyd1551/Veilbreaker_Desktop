package com.veilbreaker.companion

import org.json.JSONObject
import java.util.Locale

/** A report of a saved phone capture. It does not add to or modify evidence. */
object CaptureReportContent {
    fun build(capture: JSONObject, plan: JSONObject): String {
        require(capture.optString("format") == "veilbreaker.android.cellular" && capture.optInt("schema_version") == 1) { "Unsupported phone capture." }
        val observations = capture.optJSONArray("observations") ?: throw IllegalArgumentException("Capture observations unavailable.")
        val collection = capture.optJSONObject("collection") ?: JSONObject()
        val lines = mutableListOf("VEILBREAKER MOBILE - FIELD REPORT", "",
            "Saved phone capture: ${capture.optString("capture_id", "Unavailable")}",
            "Created (UTC): ${capture.optString("created_utc", "Unavailable")}",
            "Collection: ${collection.optString("mode", "Unknown")} / ${collection.optString("outcome", "Unknown")}",
            "Observations: ${observations.length()}", "",
            "This is captured phone evidence; it is not a continuous measurement or a network performance test.",
            "Unreported measurements remain unknown. Sample age is measured at receipt.", "", "LOCATION")
        val locations = (0 until minOf(observations.length(), 4096)).mapNotNull { observations.optJSONObject(it)?.optJSONObject("location") }
        val location = locations.lastOrNull()
        if (location == null) lines.add("Location not recorded.")
        else {
            lines.add(LocationEvidence.describeCaptured(location))
            val lat=(location.opt("latitude_deg") as? Number)?.toDouble()
            val lon=(location.opt("longitude_deg") as? Number)?.toDouble()
            if(location.optString("status") == "available" && lat != null && lon != null && lat.isFinite() && lon.isFinite() && lat in -90.0..90.0 && lon in -180.0..180.0)
                lines.add(String.format(Locale.US,"Last recorded coordinates: %.6f, %.6f",lat,lon))
            if(locations.size > 1) lines.add("${locations.size} observations included location; coordinates shown are the last recorded fix.")
        }
        lines.add(""); lines.add("CELLULAR OBSERVATIONS")
        lines.add(runCatching { CellularOverview.render(capture,plan) }.getOrElse { "Cellular details unavailable. Review the original JSON capture." })
        lines.add(""); lines.add("Report is a readable summary. Export the original JSON for complete captured evidence.")
        val report=lines.joinToString("\n")
        return if(report.length <= 120000) report else report.take(120000) + "\n\nReport text truncated. Export the original JSON for complete captured evidence."
    }
}
