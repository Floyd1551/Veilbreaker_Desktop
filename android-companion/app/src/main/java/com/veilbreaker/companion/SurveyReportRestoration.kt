package com.veilbreaker.companion

import org.json.JSONObject

/** Rebuild the view only when it was requested; exports remain independent snapshots. */
object SurveyReportRestoration {
    fun restore(requested: Boolean, savedSurvey: JSONObject, plan: JSONObject?): MobileSurveyReport.Report? =
        if (requested) MobileSurveyReport.build(savedSurvey, plan) else null
}
