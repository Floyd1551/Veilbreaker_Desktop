package com.veilbreaker.companion

import org.json.JSONObject
import java.time.Instant

object LocationEvidence {
    fun unavailable(status: String, provider: String = "gnss"): JSONObject = JSONObject()
        .put("status",status).put("source","phone").put("provider",provider)
    fun fix(latitude: Double, longitude: Double, accuracy: Double?, fixUtcMs: Long,
            fixElapsedMs: Long, receiptElapsedMs: Long, provider: String, mock: Boolean): JSONObject {
        if (!latitude.isFinite() || latitude !in -90.0..90.0 || !longitude.isFinite() || longitude !in -180.0..180.0 ||
            accuracy == null || !accuracy.isFinite() || accuracy < 0 || fixElapsedMs < 0 || fixElapsedMs > receiptElapsedMs)
            return unavailable("unavailable",provider)
        return JSONObject().put("status","available").put("source","phone").put("provider",provider)
            .put("latitude_deg",latitude).put("longitude_deg",longitude).put("horizontal_accuracy_m",accuracy)
            .put("fix_utc",Instant.ofEpochMilli(fixUtcMs).toString()).put("fix_age_ms",receiptElapsedMs-fixElapsedMs)
            .put("fix_elapsed_realtime_ms",fixElapsedMs).put("mock",mock)
    }
}
