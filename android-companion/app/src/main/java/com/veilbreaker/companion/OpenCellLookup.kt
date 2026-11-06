package com.veilbreaker.companion

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.Locale

/** An explicitly requested community database lookup, never a captured measurement. */
object OpenCellLookup {
    data class Query(val mcc: Int, val mnc: Int, val area: Long, val cellId: Long, val radio: String)
    data class Candidate(val latitude: Double, val longitude: Double, val samples: Long?, val rangeMeters: Long?)

    fun query(mcc: String, mnc: String, area: String, cellId: String, radio: String): Query? {
        if (!mcc.matches(Regex("[0-9]{3}")) || !mnc.matches(Regex("[0-9]{2,3}")) ||
            !area.matches(Regex("[0-9]{1,10}")) || !cellId.matches(Regex("[0-9]{1,11}"))) return null
        val a = area.toLongOrNull() ?: return null
        val c = cellId.toLongOrNull() ?: return null
        if (a > 4294967295L || c > 68719476735L || radio !in setOf("GSM", "UMTS", "LTE", "NR")) return null
        return Query(mcc.toInt(), mnc.toInt(), a, c, radio)
    }

    fun parse(body: String, q: Query): Candidate? = runCatching {
        val json = JSONObject(body)
        if (json.has("error") || json.optInt("mcc", -1) != q.mcc || json.optInt("mnc", -1) != q.mnc ||
            json.optLong("lac", -1) != q.area || json.optLong("cellid", -1) != q.cellId ||
            json.optString("radio", "").uppercase(Locale.ROOT) != q.radio) return null
        val lat = json.optDouble("lat", Double.NaN)
        val lon = json.optDouble("lon", Double.NaN)
        if (!lat.isFinite() || !lon.isFinite() || lat !in -90.0..90.0 || lon !in -180.0..180.0) return null
        Candidate(lat, lon, json.optLong("samples", -1).takeIf { it > 0 }, json.optLong("range", -1).takeIf { it >= 0 })
    }.getOrNull()

    /** Avoid returning server text or request URLs: some errors echo the private key. */
    fun lookup(key: String, q: Query): String {
        val encoded = URLEncoder.encode(key, "UTF-8")
        val url = URL("https://opencellid.org/cell/get?key=$encoded&mcc=${q.mcc}&mnc=${q.mnc}&lac=${q.area}&cellid=${q.cellId}&radio=${q.radio}&format=json")
        return try {
            val conn = url.openConnection() as HttpURLConnection
            try {
                conn.instanceFollowRedirects = false
                conn.connectTimeout = 10000; conn.readTimeout = 10000
                conn.setRequestProperty("Accept", "application/json")
                val status = conn.responseCode
                if (status != 200) return when (status) {
                    401, 403 -> "OpenCellID rejected the key or access. Check your account and permissions."
                    429 -> "OpenCellID request limit reached. Try again later."
                    else -> "OpenCellID lookup failed (HTTP $status). Try again later."
                }
                val body = conn.inputStream.bufferedReader().use { it.readTextLimited(16384) }
                val json = runCatching { JSONObject(body) }.getOrNull()
                if (json?.has("error") == true) return when (json.optInt("code")) {
                    1 -> "No matching cell was returned, or the service is temporarily unavailable."
                    7 -> "OpenCellID request limit reached. Try again later."
                    else -> "OpenCellID could not complete the lookup. Check the identifiers and account."
                }
                val result = parse(body, q) ?: return "The response could not be verified for these identifiers."
                "Community candidate for ${q.radio} ${q.mcc}/${q.mnc}, area ${q.area}, cell ${q.cellId}: ${result.latitude}, ${result.longitude}\n" +
                    "Samples: ${result.samples?.toString() ?: "not provided"} · Reported range: ${result.rangeMeters?.let { "$it m" } ?: "not provided"}\n" +
                    "Source: OpenCellID (CC BY-SA 4.0), retrieved ${java.time.Instant.now()}. The position is estimated, may be stale, and is not a verified tower, serving antenna, or line of sight."
            } finally { conn.disconnect() }
        } catch (_: Exception) { "Network or response error. Check your connection and try again." }
    }

    private fun java.io.Reader.readTextLimited(limit: Int): String {
        val chars = CharArray(limit + 1)
        var used = 0
        while (used < chars.size) {
            val count = read(chars, used, chars.size - used)
            if (count < 0) break
            if (count == 0) continue
            used += count
        }
        require(used <= limit)
        return String(chars, 0, used)
    }
}
