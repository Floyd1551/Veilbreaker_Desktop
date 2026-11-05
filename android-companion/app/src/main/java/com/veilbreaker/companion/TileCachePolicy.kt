package com.veilbreaker.companion

import java.text.SimpleDateFormat
import java.util.Locale
import java.util.TimeZone

/** Validated XYZ coordinate: z <= 19 limits memory and request complexity. */
data class TileKey(val z: Int, val x: Int, val y: Int) {
    fun valid(): Boolean = z in 0..19 && x >= 0 && y >= 0 && x < (1 shl z) && y < (1 shl z)
}

internal object TileCachePolicy {
    private const val FALLBACK_MS = 7L * 24 * 60 * 60 * 1000
    fun expiry(now: Long, cacheControl: String?, expires: String?, date: String?): Long? {
        val directives = cacheControl.orEmpty().lowercase(Locale.US).split(',').map { it.trim() }
        if ("no-store" in directives || "private" in directives) return null
        if ("no-cache" in directives || "must-revalidate" in directives && directives.none { it.startsWith("max-age=") }) return now
        val maxAge = directives.firstOrNull { it.startsWith("max-age=") }?.substringAfter('=')?.trim(' ', '"')?.toLongOrNull()
        if (maxAge != null && maxAge >= 0 && maxAge <= (Long.MAX_VALUE - now) / 1000) return now + maxAge * 1000
        fun parse(value: String?): Long? = try {
            if (value == null) null else SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss zzz", Locale.US).apply { timeZone = TimeZone.getTimeZone("GMT"); isLenient = false }.parse(value)?.time
        } catch (_: Exception) { null }
        val deadline = parse(expires)
        if (deadline != null) return now + (deadline - (parse(date) ?: now)).coerceAtLeast(0).coerceAtMost(Long.MAX_VALUE - now)
        return now + FALLBACK_MS
    }
}
