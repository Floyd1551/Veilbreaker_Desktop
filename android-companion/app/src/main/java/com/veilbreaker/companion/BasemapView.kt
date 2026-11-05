package com.veilbreaker.companion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.MotionEvent
import android.view.ScaleGestureDetector
import android.view.View
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.min

/** Explicitly activated, foreground-only online street map. Location remains local;
 * viewport tile coordinates are sent to the tile provider while enabled. */
class BasemapView(context: Context) : View(context) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
    private var tiles: OnlineTileRepository? = null
    private var enabledMap = false
    private var saved: List<GpsSpatialModel.Fix> = emptyList()
    private var labels: List<String>? = null
    private var live: GpsSpatialModel.Fix? = null
    // A neutral initial overview, not a claim about the device's location.
    private var latitude = 39.8
    private var longitude = -98.6
    private var zoom = 3
    private var lastX = 0f
    private var lastY = 0f
    private var scale = 1f
    private val density get() = resources.displayMetrics.density
    private val scaleDetector = ScaleGestureDetector(context, object : ScaleGestureDetector.SimpleOnScaleGestureListener() {
        override fun onScaleBegin(detector: ScaleGestureDetector): Boolean { scale = 1f; return true }
        override fun onScale(detector: ScaleGestureDetector): Boolean {
            scale *= detector.scaleFactor
            if (scale >= 1.7f) { zoomIn(); scale = 1f }
            if (scale <= 0.59f) { zoomOut(); scale = 1f }
            return true
        }
    })

    init { contentDescription = "Online street map. Saved and live GPS positions are also described in text." }

    fun setActive(active: Boolean) {
        if (active == enabledMap) return
        enabledMap = active
        if (active) tiles = OnlineTileRepository(context.applicationContext) { if (enabledMap) postInvalidateOnAnimation() }
        else { tiles?.close(); tiles = null }
        invalidate()
    }
    fun setFixes(values: List<GpsSpatialModel.Fix>, current: GpsSpatialModel.Fix?) { saved = values; live = current; invalidate() }
    fun setSavedLabels(values: List<String>?) { labels = values; invalidate() }
    fun fitToPoints() {
        if (width <= 0 || height <= 0) { post { if (isAttachedToWindow) fitToPoints() }; return }
        val fixes = saved + listOfNotNull(live)
        val camera = BasemapCamera.fit(fixes.map { it.latitude to it.longitude }, (width / density).toInt(), (height / density).toInt()) ?: return
        latitude = camera.latitude; longitude = camera.longitude; zoom = camera.zoom; invalidate()
    }
    fun zoomIn() { zoom = (zoom + 1).coerceAtMost(18); invalidate() }
    fun zoomOut() { zoom = (zoom - 1).coerceAtLeast(2); invalidate() }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        paint.style = Paint.Style.FILL; paint.color = Color.rgb(12, 23, 36)
        canvas.drawColor(paint.color)
        if (!enabledMap || width <= 0 || height <= 0) return
        val repository = tiles ?: return
        val center = WebMercator.project(latitude, longitude, zoom)
        val visible = WebMercator.visibleTiles(center.first, center.second, zoom, (width / density).toInt().coerceAtMost(8192), (height / density).toInt().coerceAtMost(8192))
        val keys = visible.map { TileKey(zoom, it.x, it.y) }.toSet()
        repository.updateViewport(keys)
        var missing = 0
        visible.forEach { tile ->
            val bitmap = repository.get(TileKey(zoom, tile.x, tile.y))
            if (bitmap == null) { missing++; return@forEach }
            val left = ((tile.displayX * 256.0 - center.first) * density + width / 2.0).toFloat()
            val top = ((tile.y * 256.0 - center.second) * density + height / 2.0).toFloat()
            paint.color = Color.WHITE; paint.alpha = 255
            canvas.drawBitmap(bitmap, null, RectF(left, top, left + 256f * density, top + 256f * density), paint)
        }
        val world = WebMercator.worldSize(zoom)
        val all = saved + listOfNotNull(live)
        all.forEachIndexed { index, fix ->
            if (fix.latitude !in -85.05112878..85.05112878) return@forEachIndexed
            val projected = WebMercator.project(fix.latitude, fix.longitude, zoom)
            val x = (width / 2.0 + WebMercator.wrappedDelta(projected.first, center.first, world) * density).toFloat()
            val y = (height / 2.0 + (projected.second - center.second) * density).toFloat()
            val color = if (index >= saved.size) Color.rgb(42, 221, 204) else Color.rgb(189, 132, 255)
            val metersPerPixel = cos(Math.toRadians(fix.latitude.coerceIn(-85.0, 85.0))) * 2 * PI * 6378137.0 / world
            val radius = min((fix.accuracy / metersPerPixel * density).toFloat(), maxOf(width, height) * 4f)
            if (radius > 0f) {
                paint.color = color; paint.alpha = 140; paint.style = Paint.Style.STROKE; paint.strokeWidth = 2f * density
                canvas.drawCircle(x, y, radius, paint); paint.style = Paint.Style.FILL; paint.alpha = 255
            }
            paint.color = Color.BLACK; canvas.drawCircle(x, y, 8f * density, paint)
            paint.color = color; canvas.drawCircle(x, y, 6f * density, paint)
            val label = if (index < saved.size) labels?.getOrNull(index) else null
            if (label != null) {
                paint.color = Color.BLACK; paint.style = Paint.Style.STROKE; paint.strokeWidth = 3f * density; paint.textSize = 12f * resources.displayMetrics.scaledDensity
                canvas.drawText(label, x + 8f * density, y - 7f * density, paint)
                paint.style = Paint.Style.FILL; paint.color = Color.WHITE
                canvas.drawText(label, x + 8f * density, y - 7f * density, paint)
            }
        }
        // Backed labels remain legible on both light and dark map tiles.
        paint.textSize = 11f * resources.displayMetrics.scaledDensity
        if (missing > 0 || visible.isEmpty()) drawBanner(canvas, "Map tiles loading or unavailable", 0f)
        else if (all.any { it.latitude !in -85.05112878..85.05112878 }) drawBanner(canvas, "Polar fixes unavailable in this projection", 0f)
        drawBanner(canvas, "© OpenStreetMap contributors", height - 20f * density)
    }

    private fun drawBanner(canvas: Canvas, text: String, top: Float) {
        val height = 20f * density
        paint.color = Color.argb(220, 5, 15, 25); paint.style = Paint.Style.FILL
        canvas.drawRect(0f, top, width.toFloat(), top + height, paint)
        paint.color = Color.WHITE; paint.textSize = 11f * resources.displayMetrics.scaledDensity
        canvas.drawText(text, 6f * density, top + 14f * density, paint)
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (!enabledMap) return false
        scaleDetector.onTouchEvent(event)
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> { parent?.requestDisallowInterceptTouchEvent(true); lastX = event.x; lastY = event.y }
            MotionEvent.ACTION_MOVE -> {
                if (event.pointerCount == 1 && !scaleDetector.isInProgress) {
                    val center = WebMercator.project(latitude, longitude, zoom)
                    val world = WebMercator.worldSize(zoom)
                    val next = WebMercator.unproject(center.first - (event.x - lastX) / density, (center.second - (event.y - lastY) / density).coerceIn(0.0, world), zoom)
                    latitude = next.first; longitude = next.second; invalidate()
                }
                lastX = event.x; lastY = event.y
            }
            MotionEvent.ACTION_POINTER_UP -> { lastX = event.x; lastY = event.y }
            MotionEvent.ACTION_UP -> { parent?.requestDisallowInterceptTouchEvent(false); performClick() }
            MotionEvent.ACTION_CANCEL -> parent?.requestDisallowInterceptTouchEvent(false)
        }
        return true
    }
    override fun performClick(): Boolean { super.performClick(); return true }
    override fun onDetachedFromWindow() { setActive(false); super.onDetachedFromWindow() }
}
