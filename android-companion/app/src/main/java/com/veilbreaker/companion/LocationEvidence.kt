package com.veilbreaker.companion

import org.json.JSONObject
import java.time.Instant

object LocationEvidence {
    fun unavailable(status: String, provider: String = "gnss"): JSONObject = JSONObject()
        .put("status",status).put("source","phone").put("provider",provider.ifBlank { "gnss" })
    fun fix(latitude: Double, longitude: Double, accuracy: Double?, fixUtcMs: Long,
            fixElapsedMs: Long, receiptElapsedMs: Long, provider: String, mock: Boolean): JSONObject {
        if (!latitude.isFinite() || latitude !in -90.0..90.0 || !longitude.isFinite() || longitude !in -180.0..180.0 ||
            accuracy == null || !accuracy.isFinite() || accuracy !in 0.0..1e9 || fixElapsedMs < 0 || fixElapsedMs > receiptElapsedMs)
            return unavailable("unavailable",provider)
        return JSONObject().put("status","available").put("source","phone").put("provider",provider.ifBlank { "gnss" })
            .put("latitude_deg",latitude).put("longitude_deg",longitude).put("horizontal_accuracy_m",accuracy)
            .put("fix_utc",Instant.ofEpochMilli(fixUtcMs).toString()).put("fix_age_ms",receiptElapsedMs-fixElapsedMs)
            .put("fix_elapsed_realtime_ms",fixElapsedMs).put("mock",mock)
    }

    /** Optional fields obey the same finite bounds as the desktop Android capture schema. */
    fun addOptional(fix: JSONObject, altitude: Double?, verticalAccuracy: Double?, speed: Double?, bearing: Double?): JSONObject {
        if (fix.optString("status") != "available") return fix
        if (altitude != null && altitude.isFinite() && altitude in -1e6..1e7)
            fix.put("altitude_m",altitude).put("altitude_reference","ellipsoid")
        if (verticalAccuracy != null && verticalAccuracy.isFinite() && verticalAccuracy in 0.0..1e15)
            fix.put("vertical_accuracy_m",verticalAccuracy)
        if (speed != null && speed.isFinite() && speed in 0.0..1e15)
            fix.put("speed_mps",speed)
        if (bearing != null && bearing.isFinite() && bearing >= 0.0 && bearing < 360.0)
            fix.put("bearing_deg",bearing)
        return fix
    }

    /** Saved location quality describes the fix at collection, not the device's current status. */
    fun describeCaptured(fix: JSONObject): String {
        if (fix.optString("status") != "available") return when (fix.optString("status")) {
            "permission_denied" -> "Location permission unavailable at capture"
            "disabled" -> "Location disabled at capture"
            else -> "Location unavailable at capture"
        }
        val age = (fix.opt("fix_age_ms") as? Number)?.toLong()?.takeIf { it >= 0 }
        val accuracy = (fix.opt("horizontal_accuracy_m") as? Number)?.toDouble()?.takeIf { it.isFinite() && it >= 0 }
        val quality = when {
            fix.optBoolean("mock") -> "Test location at capture"
            age != null && age > 10000 -> "Old fix at capture"
            accuracy != null && accuracy > 25 -> "Low accuracy at capture"
            else -> "Captured fix"
        }
        val accuracyText = accuracy?.let { "±${it.toInt()} m" } ?: "accuracy unavailable"
        val ageText = age?.let { "${it / 1000}s old at receipt" } ?: "age unavailable at receipt"
        return "$quality · $accuracyText · $ageText"
    }
}
