package com.veilbreaker.companion

import org.json.JSONObject

/** A read-only presentation of the survey; it never alters original captures. */
object MobileSurveyReport {
    data class Report(val name: String, val surveyId: String, val lifecycle: String,
        val createdUtc: String, val points: List<SurveyComparisonModel.Point>,
        val completeCount: Int, val partialCount: Int, val locations: Map<Int, GpsSpatialModel.Fix>)

    fun build(survey: JSONObject, plan: JSONObject?): Report {
        MobileSurvey.validate(survey)
        val points = SurveyComparisonModel.build(survey, plan)
        return Report(survey.getString("name"), survey.getString("survey_id"),
            survey.getString("lifecycle"), survey.getString("created_utc"), points,
            points.count { it.outcome == "complete" }, points.count { it.outcome == "partial" },
            GpsSpatialModel.surveyLocations(survey).associate { it.pointNumber to it.fix })
    }

    private fun escape(value: String): String = buildString {
        for (ch in value) append(when (ch) {
            '&' -> "&amp;"; '<' -> "&lt;"; '>' -> "&gt;"; '"' -> "&quot;"; '\'' -> "&#39;"
            else -> ch.toString()
        })
    }

    /** Self-contained HTML. Every operator/device string is encoded as text. */
    fun html(report: Report): String = buildString {
        fun para(value: String) { append("<p>").append(escape(value).replace("\n", "<br>")).append("</p>") }
        append("<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>Mobile survey report</title>")
        append("<style>body{font:16px sans-serif;line-height:1.45;max-width:70rem;margin:auto;padding:1.5rem;color:#172131}h1,h2{color:#126759}section{border:1px solid #ccd6df;padding:1rem;margin:1rem 0}p{overflow-wrap:anywhere}</style></head><body>")
        append("<h1>Mobile survey report</h1><h2>").append(escape(report.name)).append("</h2>")
        para("Survey ${report.surveyId} · ${report.lifecycle} · created ${report.createdUtc}")
        para("${report.points.size} captures · ${report.completeCount} complete · ${report.partialCount} partial. Other outcomes remain identified per point.")
        para("Values are saved observations, not live. Cell and location readings can have different times. Compare equivalent technology, SIM, cell, band and receiver settings; no transmitter location or signal coverage is inferred.")
        if (report.points.isEmpty()) para("No captures are saved in this survey.")
        for (point in report.points) {
            append("<section><h2>Point ").append(point.number).append("</h2>")
            para("Capture ${point.captureId} · ${point.outcome} · created ${point.createdUtc}")
            para(point.location)
            report.locations[point.number]?.let { para("Last reported receiver coordinates: ${it.latitude}, ${it.longitude}") }
            point.operatorNote?.let { para("Operator observation (not measured): $it") }
            if (point.servingCells.isEmpty()) para("No registered serving cell reported in the latest observations.")
            for (cell in point.servingCells) {
                para("${cell.radio} · ${cell.role} · ${cell.subscription} · ${cell.carrier} · ${cell.band}")
                para("${cell.age} · observation assembled ${cell.received}" +
                    (cell.cellResponseReceived?.let { " · cell response received $it; location may have been acquired separately" } ?: ""))
                para(cell.identity.joinToString(" · "))
                para(cell.metrics.joinToString(" · "))
            }
            if (point.omittedServing > 0 || point.inventoryIncomplete) para("Some cell or observation data is not shown. Shown cells may not be latest; inspect the original capture.")
            append("</section>")
        }
        para("Original captures remain in the survey JSON. This report is a readable snapshot, not a replacement for original evidence.")
        append("</body></html>")
    }
}
