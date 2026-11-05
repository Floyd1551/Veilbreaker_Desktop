package com.veilbreaker.companion

import android.content.Context
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.os.Handler
import android.os.Looper
import android.util.LruCache
import java.io.ByteArrayOutputStream
import java.io.File
import java.net.HttpURLConnection
import java.net.URL
import java.util.Properties
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit

/** Online-only viewport tile requests. Callbacks are delivered on the main thread. */
class OnlineTileRepository(context: Context, private val onChanged: () -> Unit) {
    private val cacheDir = File(context.cacheDir, "online-osm-tiles").apply { mkdirs() }
    private val handler = Handler(Looper.getMainLooper())
    private val executor = ThreadPoolExecutor(1, 1, 0, TimeUnit.SECONDS, LinkedBlockingQueue<Runnable>())
    private data class MemoryTile(val bitmap: Bitmap, val expiresAt: Long, val viewport: Long, val ephemeral: Boolean)
    private val memory = object : LruCache<TileKey, MemoryTile>(96) {}
    private var viewport = 0L
    private val lock = Any()
    private var wanted: Set<TileKey> = emptySet()
    private var closed = false
    private var active: TileKey? = null
    private var connection: HttpURLConnection? = null
    private val scheduled = mutableSetOf<TileKey>()
    private val retryAfter = mutableMapOf<TileKey, Long>()
    private val maxTileBytes = 512 * 1024
    private val maxCacheBytes = 24L * 1024 * 1024

    private fun usable(key: TileKey, now: Long): MemoryTile? {
        val value = memory.get(key) ?: return null
        if (value.expiresAt > now || value.ephemeral && value.viewport == viewport) return value
        memory.remove(key)
        return null
    }
    fun get(key: TileKey): Bitmap? = synchronized(lock) {
        if (closed || key !in wanted) null else usable(key, System.currentTimeMillis())?.bitmap
    }

    /** Only the supplied viewport is ever requested; a changed viewport cancels obsolete work. */
    fun updateViewport(keys: Set<TileKey>) {
        var obsolete: HttpURLConnection? = null
        synchronized(lock) {
            if (closed) return
            val next = keys.asSequence().filter { it.valid() }.take(64).toSet()
            if (next != wanted) {
                wanted = next
                viewport++
                executor.queue.clear()
                scheduled.clear()
                active?.let { scheduled.add(it) }
                if (active !in wanted) obsolete = connection
            }
            val now = System.currentTimeMillis()
            retryAfter.keys.retainAll(wanted)
            for (key in wanted) {
                if (usable(key, now) == null && key !in scheduled && (retryAfter[key] ?: 0L) <= now) {
                    scheduled.add(key)
                    executor.execute { fetch(key) }
                }
            }
        }
        obsolete?.let { disconnectAsync(it) }
    }

    fun close() {
        val old: HttpURLConnection?
        synchronized(lock) {
            if (closed) return
            closed = true; wanted = emptySet(); scheduled.clear()
            memory.evictAll(); old = connection
            executor.queue.clear(); executor.shutdownNow()
        }
        old?.let { disconnectAsync(it) }
    }

    private fun disconnectAsync(value: HttpURLConnection) {
        Thread({ try { value.disconnect() } catch (_: Exception) {} }, "Veilbreaker map disconnect").apply { isDaemon = true; start() }
    }
    private fun stillWanted(key: TileKey) = synchronized(lock) { !closed && key in wanted && !Thread.currentThread().isInterrupted }
    private fun tileFile(key: TileKey) = File(cacheDir, "${key.z}_${key.x}_${key.y}.png")
    private fun metadataFile(key: TileKey) = File(cacheDir, "${key.z}_${key.x}_${key.y}.meta")
    private fun loadMetadata(key: TileKey): Properties? = try {
        Properties().also { metadataFile(key).inputStream().use(it::load) }
    } catch (_: Exception) { null }
    private fun saveMetadata(key: TileKey, p: Properties) {
        val target = metadataFile(key)
        val temp = File(cacheDir, target.name + ".tmp")
        temp.outputStream().use { p.store(it, null) }
        if (!temp.renameTo(target)) { target.delete(); if (!temp.renameTo(target)) temp.delete() }
    }
    private fun decode(bytes: ByteArray): Bitmap? {
        if (bytes.size < 8 || !bytes.copyOfRange(0, 8).contentEquals(byteArrayOf(-119, 80, 78, 71, 13, 10, 26, 10))) return null
        val probe = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, probe)
        if (probe.outWidth != 256 || probe.outHeight != 256 || probe.outMimeType != "image/png") return null
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size)
    }
    private fun readCached(key: TileKey): Pair<ByteArray, Properties>? {
        val file = tileFile(key)
        if (!file.isFile || file.length() !in 1..maxTileBytes.toLong()) return null
        val p = loadMetadata(key) ?: return null
        return try { Pair(file.readBytes(), p) } catch (_: Exception) { null }
    }
    private fun postBitmap(key: TileKey, bitmap: Bitmap, expiresAt: Long?, requestViewport: Long) {
        synchronized(lock) {
            if (closed || key !in wanted) return
            val now = System.currentTimeMillis()
            // A no-store/no-cache response may be drawn for the viewport that requested it,
            // but is never reused for a later viewport without revalidation.
            memory.put(key, MemoryTile(bitmap, expiresAt ?: now, requestViewport, expiresAt == null || expiresAt <= now))
        }
        handler.post { if (stillWanted(key)) onChanged() }
    }
    private fun fetch(key: TileKey) {
        val requestViewport = synchronized(lock) {
            if (closed || key !in wanted) { scheduled.remove(key); return }
            active = key
            viewport
        }
        var succeeded = false
        var c: HttpURLConnection? = null
        try {
            val cached = readCached(key)
            val now = System.currentTimeMillis()
            if (cached != null && (cached.second.getProperty("expiresAt")?.toLongOrNull() ?: 0) > now) {
                val bitmap = decode(cached.first)
                if (bitmap != null) {
                    tileFile(key).setLastModified(now); postBitmap(key, bitmap, cached.second.getProperty("expiresAt").toLong(), requestViewport); succeeded = true; return
                }
            }
            if (!stillWanted(key)) return
            c = URL("https://tile.openstreetmap.org/${key.z}/${key.x}/${key.y}.png").openConnection() as HttpURLConnection
            c.connectTimeout = 8000; c.readTimeout = 8000; c.instanceFollowRedirects = false
            c.setRequestProperty("User-Agent", "VeilbreakerMobile/0.8 (+https://github.com/Floyd1551/Veilbreaker_Desktop)")
            cached?.second?.getProperty("etag")?.takeIf { it.isNotBlank() }?.let { c.setRequestProperty("If-None-Match", it) }
            cached?.second?.getProperty("lastModified")?.takeIf { it.isNotBlank() }?.let { c.setRequestProperty("If-Modified-Since", it) }
            synchronized(lock) { if (closed || key !in wanted) return; connection = c }
            val status = c.responseCode
            if (!stillWanted(key)) return
            val bytes = when (status) {
                HttpURLConnection.HTTP_NOT_MODIFIED -> cached?.first ?: return
                HttpURLConnection.HTTP_OK -> {
                    if (c.contentLengthLong > maxTileBytes) return
                    val out = ByteArrayOutputStream(); val buffer = ByteArray(8192)
                    c.inputStream.use { input ->
                        while (true) {
                            if (!stillWanted(key)) return
                            val n = input.read(buffer); if (n < 0) break
                            if (n == 0) continue
                            if (out.size() + n > maxTileBytes) return
                            out.write(buffer, 0, n)
                        }
                    }
                    out.toByteArray()
                }
                else -> return
            }
            val bitmap = decode(bytes) ?: return
            if (!stillWanted(key)) return
            val headers = Properties()
            fun header(name: String, prop: String): String? = c.getHeaderField(name) ?: if (status == HttpURLConnection.HTTP_NOT_MODIFIED) cached?.second?.getProperty(prop) else null
            val control = header("Cache-Control", "cacheControl")
            val expires = header("Expires", "expires")
            val date = c.getHeaderField("Date")
            val expiry = TileCachePolicy.expiry(System.currentTimeMillis(), control, expires, date)
            if (expiry != null) {
                headers.setProperty("expiresAt", expiry.toString())
                control?.let { headers.setProperty("cacheControl", it) }
                expires?.let { headers.setProperty("expires", it) }
                header("ETag", "etag")?.let { headers.setProperty("etag", it) }
                header("Last-Modified", "lastModified")?.let { headers.setProperty("lastModified", it) }
                try {
                    val file = tileFile(key); val tmp = File(cacheDir, file.name + ".tmp")
                    tmp.writeBytes(bytes)
                    if (!tmp.renameTo(file)) { file.delete(); if (!tmp.renameTo(file)) tmp.delete() }
                    saveMetadata(key, headers); prune()
                } catch (_: Exception) { /* Map remains usable without disk caching. */ }
            } else { tileFile(key).delete(); metadataFile(key).delete() }
            postBitmap(key, bitmap, expiry, requestViewport); succeeded = true
        } catch (_: Exception) { /* Network unavailable; display the map's missing tile state. */ }
        finally {
            c?.disconnect()
            synchronized(lock) {
                if (active == key) { active = null; connection = null }
                scheduled.remove(key)
                if (!succeeded && !closed && key in wanted) retryAfter[key] = System.currentTimeMillis() + 30000
            }
        }
    }
    private fun prune() {
        val tiles = cacheDir.listFiles { f -> f.name.endsWith(".png") }?.sortedBy { it.lastModified() } ?: return
        var size = tiles.sumOf { it.length() }
        for (f in tiles) {
            if (size <= maxCacheBytes) break
            size -= f.length(); f.delete(); File(cacheDir, f.name.removeSuffix(".png") + ".meta").delete()
        }
    }
}
