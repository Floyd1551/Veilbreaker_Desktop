package com.veilbreaker.companion

import org.json.JSONObject

/** Plot-only data, never fed back into capture evidence. */
object GpsSpatialModel {
    data class Fix(val latitude: Double, val longitude: Double, val accuracy: Double,
                   val ageAtReceiptMs: Long?, val provider: String?, val mock: Boolean,
                   val receivedUtc: String? = null)
    data class Bounds(val west: Double, val south: Double, val east: Double, val north: Double)

    fun bounds(west: Double, south: Double, east: Double, north: Double): Bounds? {
        if (!listOf(west, south, east, north).all { it.isFinite() } || west !in -180.0..180.0 ||
            east !in -180.0..180.0 || south !in -90.0..90.0 || north !in -90.0..90.0 ||
            west >= east || south >= north || east - west > 180.0) return null
        return Bounds(west, south, east, north)
    }

    /** North-up Plate Carrée image coordinates; no dateline wrap or reprojection. */
    fun mapPoint(bounds: Bounds, lat: Double, lon: Double): Pair<Double, Double>? {
        if (!lat.isFinite() || !lon.isFinite() || lat !in bounds.south..bounds.north || lon !in bounds.west..bounds.east) return null
        return Pair((lon - bounds.west) / (bounds.east - bounds.west), (bounds.north - lat) / (bounds.north - bounds.south))
    }

    fun fix(location: JSONObject?, receivedUtc: String? = null): Fix? {
        if (location == null || location.optString("status") != "available") return null
        val lat = (location.opt("latitude_deg") as? Number)?.toDouble() ?: return null
        val lon = (location.opt("longitude_deg") as? Number)?.toDouble() ?: return null
        val accuracy = (location.opt("horizontal_accuracy_m") as? Number)?.toDouble() ?: return null
        if (!lat.isFinite() || !lon.isFinite() || !accuracy.isFinite() || lat !in -90.0..90.0 ||
            lon !in -180.0..180.0 || accuracy !in 0.0..1e9) return null
        val age = (location.opt("fix_age_ms") as? Number)?.toLong()?.takeIf { it >= 0 }
        return Fix(lat, lon, accuracy, age, location.optString("provider").ifBlank { null },
                   location.optBoolean("mock", false), receivedUtc)
    }

    fun savedFixes(capture: JSONObject?): List<Fix> {
        val observations = capture?.optJSONArray("observations") ?: return emptyList()
        val result = mutableListOf<Fix>()
        // Capture contract bounds observations; still cap reads if a local file is damaged.
        for (index in 0 until minOf(observations.length(), 4096)) {
            val observation = observations.optJSONObject(index) ?: continue
            fix(observation.optJSONObject("location"), observation.optString("received_utc").ifBlank { null })?.let(result::add)
        }
        return result
    }

    /** Reject decompression bombs before decoding, then cap the in-memory image. */
    fun imageSampleSize(width: Int, height: Int): Int? {
        if (width <= 0 || height <= 0 || width > 12000 || height > 12000 || width.toLong() * height > 64_000_000L) return null
        var sample = 1
        while ((width + sample - 1) / sample > 2048 || (height + sample - 1) / sample > 2048) sample *= 2
        return sample
    }

    /** Missing metadata is allowed, but any explicitly non-normal or malformed orientation is rejected. */
    fun isMapOrientationSafe(exifOrientation: String?): Boolean = exifOrientation == null || exifOrientation == "1"
}
