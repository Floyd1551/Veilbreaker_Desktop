package com.veilbreaker.companion

/** Per-capture evidence availability, not a health or comparability assessment. */
object SurveyEvidenceOverview {
    data class Summary(
        val captures: Int,
        val withLocation: Int,
        val withoutLocation: Int,
        val withLocationTimes: Int,
        val mockMarked: Int,
        val mockUnknown: Int,
        val withRegisteredCellShown: Int,
        val incompleteCellReviews: Int
    ) {
        fun lines(): List<String> = listOf(
            "Reported receiver location: $withLocation of $captures captures",
            "No valid location in reviewed observations: $withoutLocation of $captures captures",
            "Fix time and location receipt time recorded: $withLocationTimes of $withLocation reported locations",
            "Marked mock: $mockMarked of $withLocation reported locations",
            "Mock status unknown: $mockUnknown of $withLocation reported locations",
            "Registered cell shown: $withRegisteredCellShown of $captures captures",
            "Cell review limited or unavailable: $incompleteCellReviews of $captures captures"
        )

        val limitations: String get() = "Counts summarize one reported location per capture, not individual observations. This is not a signal health score. " +
            "A reported location can be stale, inaccurate or mock, and its time may differ from the cellular observation. " +
            "Some cell entries or observations may be skipped or unavailable. Counts do not establish that captures are comparable."
    }

    fun summarize(points: List<SurveyComparisonModel.Point>, locations: Map<Int, GpsSpatialModel.Fix>): Summary {
        val fixes = points.mapNotNull { locations[it.number] }
        return Summary(
            captures = points.size,
            withLocation = fixes.size,
            withoutLocation = points.size - fixes.size,
            withLocationTimes = fixes.count { it.receivedUtc != null && it.fixUtc != null },
            mockMarked = fixes.count { it.mock == true },
            mockUnknown = fixes.count { it.mock == null },
            withRegisteredCellShown = points.count { it.servingCells.isNotEmpty() },
            incompleteCellReviews = points.count { it.inventoryIncomplete || it.omittedServing > 0 }
        )
    }
}
