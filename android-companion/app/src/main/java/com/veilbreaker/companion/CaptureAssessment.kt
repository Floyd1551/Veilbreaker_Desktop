package com.veilbreaker.companion

/** Capture completeness describes the requested inputs, not radio quality. */
object CaptureAssessment {
    data class Result(val outcome: String, val notes: List<String>)
    fun assess(cellular: Boolean, cellCount: Int, simPresent: Boolean, error: String?,
               location: Boolean, locationStatus: String?): Result {
        val notes = mutableListOf<String>()
        if (error != null) notes.add(error)
        if (cellular && !simPresent) notes.add("Selected SIM unavailable at capture.")
        if (cellular && cellCount == 0) notes.add("No cellular information was reported.")
        if (cellCount > 256) notes.add("Cell list truncated to 256 entries; additional modem entries omitted.")
        if (location && locationStatus != "available") notes.add("Phone location was not available at capture.")
        return Result(if (notes.isEmpty()) "complete" else "partial", notes)
    }
}
