package com.veilbreaker.companion

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.media.ExifInterface
import android.net.Uri
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.util.Locale
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.max
import kotlin.math.min

/** User-controlled, foreground-only GPS display and optional local image map. */
class GpsMapActivity : Activity() {
    private lateinit var location: PhoneLocation
    private lateinit var plot: GpsPlotView
    private lateinit var basemap: BasemapView
    private var basemapEnabled = false
    private lateinit var status: TextView
    private lateinit var mapInfo: TextView
    private lateinit var savedInfo: TextView
    private lateinit var liveButton: Button
    private lateinit var fields: List<EditText>
    private lateinit var source: EditText
    private val handler = Handler(Looper.getMainLooper())
    private var started = false
    private var visible = false
    private var pendingBounds: GpsSpatialModel.Bounds? = null
    private var pendingSource = ""
    private var saved: List<GpsSpatialModel.Fix> = emptyList()
    private var live: GpsSpatialModel.Fix? = null
    private var imageSource = ""
    private data class SavedLocations(val fixes: List<GpsSpatialModel.Fix>, val labels: List<String>?, val description: String)
    private class MapLoad(val uri: Uri, val bounds: GpsSpatialModel.Bounds, val source: String) {
        @Volatile var cancelled = false
        @Volatile var stream: InputStream? = null
        var thread: Thread? = null
    }
    private var imageLoad: MapLoad? = null
    private val tick = object : Runnable {
        override fun run() {
            if (!started) return
            val value = location.atReceipt(SystemClock.elapsedRealtime())
            val hadLiveFix = live != null
            live = GpsSpatialModel.fix(value)
            plot.setFixes(saved, live)
            basemap.setFixes(saved, live)
            if (basemapEnabled && !hadLiveFix && live != null && saved.isEmpty()) basemap.fitToPoints()
            status.text = if (live == null) "Live GPS: " + LocationEvidence.describeCaptured(value).replace("at capture", "now")
                else liveDescription(live!!)
            handler.postDelayed(this, 1000)
        }
    }

    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        location = PhoneLocation(this)
        window.statusBarColor = Color.parseColor("#0d1520")
        window.navigationBarColor = Color.parseColor("#0d1520")
        val scroll = ScrollView(this).apply { setBackgroundColor(Color.parseColor("#0d1520")); isFillViewport = true }
        val root = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(20), dp(22), dp(20), dp(24)) }
        scroll.addView(root); setContentView(scroll)
        SystemBarInsets.apply(scroll)
        fun text(value: String, size: Float = 14f) = TextView(this).apply {
            this.text = value; textSize = size; setTextColor(Color.parseColor("#d4e2ed")); setPadding(0, dp(5), 0, dp(5)); root.addView(this)
        }
        fun button(value: String, click: () -> Unit) = Button(this).apply {
            this.text = value; isAllCaps = false; minHeight = dp(48); setOnClickListener { click() }; root.addView(this)
        }
        text("GPS & MAP", 22f).apply { setTypeface(null, Typeface.BOLD); setTextColor(Color.parseColor("#63dec8")) }
        val surveyId = intent.getStringExtra("mobile_survey_id")
        text((if (surveyId == null) "Saved points come from the last phone capture. " else "Saved points come from the selected phone survey; each marker is its capture's last valid reported fix. ") +
            "Live GPS starts only when you choose it and stops when this screen leaves the foreground. No location is saved by this screen.")
        liveButton = button("Start live GPS") { if (started) stopLive() else beginLive() }
        status = text("Live GPS off. Saved points may be old; check their capture timestamps.")
        text("Cyan: live fix · Purple: saved capture fixes. Accuracy circles are approximate horizontal uncertainty, not coverage.")
        plot = GpsPlotView(this)
        root.addView(plot, LinearLayout.LayoutParams(-1, dp(270)))
        plot.setFixes(saved, null)
        basemap = BasemapView(this).apply { visibility = View.GONE }
        root.addView(basemap, LinearLayout.LayoutParams(-1, dp(350)))
        mapInfo = text("Coordinate plot only; no geographic basemap.")
        text("ONLINE STREET MAP", 17f).setTextColor(Color.parseColor("#63dec8"))
        text("Enable the map to request visible street tiles from OpenStreetMap. The provider can see your IP address and approximate viewed area. Requires internet; this is not an offline map pack. The map stops requesting tiles when you leave this screen.")
        button("Enable online street map") {
            cancelMapLoad()
            basemapEnabled = true
            plot.visibility = View.GONE
            basemap.visibility = View.VISIBLE
            basemap.setFixes(saved, live)
            basemap.setActive(true)
            basemap.fitToPoints()
            mapInfo.text = "Online street map · © OpenStreetMap contributors. Tile requests reveal the viewed area; street data is not a measurement."
        }
        val mapControls = LinearLayout(this).apply { orientation = LinearLayout.HORIZONTAL; root.addView(this) }
        fun mapButton(label: String, action: () -> Unit) = Button(this).apply {
            text = label; isAllCaps = false; setOnClickListener { if (basemapEnabled) action() }
            mapControls.addView(this, LinearLayout.LayoutParams(0, dp(48), 1f))
        }
        mapButton("−") { basemap.zoomOut() }
        mapButton("Fit points") { basemap.fitToPoints() }
        mapButton("+") { basemap.zoomIn() }
        button("Retry street map tiles") { if (basemapEnabled) { basemap.setActive(false); basemap.setActive(true) } }
        button("Disable street map / return to previous view") { showCoordinatePlot() }
        savedInfo = text("Loading saved locations…")
        loadSavedFixes(surveyId)
        text("OFFLINE IMAGE MAP", 17f).setTextColor(Color.parseColor("#63dec8"))
        text("Optional: choose a local north-up Plate Carrée / equirectangular image and enter its full WGS84 bounds. Bounds, source and north-up orientation are operator supplied and unverified. Images with rotated or mirrored EXIF orientation are rejected. Web Mercator images are not supported. No buildings or terrain are measured. The image is kept for this screen only.")
        val labels = listOf("West longitude", "South latitude", "East longitude", "North latitude")
        fields = labels.map { label ->
            EditText(this).apply { hint = label; contentDescription = label; setSingleLine(true); setTextColor(Color.WHITE); setHintTextColor(Color.LTGRAY); inputType = android.text.InputType.TYPE_CLASS_NUMBER or android.text.InputType.TYPE_NUMBER_FLAG_SIGNED or android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL; root.addView(this) }
        }
        source = EditText(this).apply { hint = "Image source / attribution"; contentDescription = "Image source and attribution"; setSingleLine(true); setTextColor(Color.WHITE); setHintTextColor(Color.LTGRAY); filters = arrayOf(android.text.InputFilter.LengthFilter(120)); root.addView(this) }
        button("Choose local map image…") {
            val values = fields.map { it.text.toString().trim().toDoubleOrNull() }
            val bounds = if (values.all { it != null }) GpsSpatialModel.bounds(values[0]!!, values[1]!!, values[2]!!, values[3]!!) else null
            if (bounds == null || source.text.toString().isBlank()) {
                status.text = "Enter finite west, south, east, north bounds and an image source. Dateline-spanning extents are not supported."
            } else {
                pendingBounds = bounds; pendingSource = source.text.toString().trim()
                startActivityForResult(Intent(Intent.ACTION_OPEN_DOCUMENT).apply { addCategory(Intent.CATEGORY_OPENABLE); type = "image/*"; putExtra(Intent.EXTRA_LOCAL_ONLY, true) }, 45)
            }
        }
        button("Remove image / show coordinate plot") { cancelMapLoad(); plot.setImage(null, null); imageSource = ""; showCoordinatePlot() }
        button("Back to field workspace") { finish() }
    }

    private fun loadSavedFixes(surveyId: String?) {
        Thread {
            val loaded = runCatching {
                if (surveyId != null) {
                    val survey = MobileSurveyStore(this).load(surveyId)
                    val locations = GpsSpatialModel.surveyLocations(survey)
                    val count = survey.getJSONArray("points").length()
                    val details = locations.map { "P${it.pointNumber} · Capture ${it.captureId} · receipt ${it.fix.receivedUtc ?: "unknown"} · ${fixDescription(it.fix, false)}" }
                    SavedLocations(locations.map { it.fix }, locations.map { "P${it.pointNumber}" },
                        (listOf("${locations.size} of $count captures have a valid reported fix. Last valid fix per capture; age, accuracy and mock status are shown below.") + details).joinToString("\n"))
                } else {
                    val file = filesDir.resolve("last-capture.json")
                    val fixes = if (!file.isFile || file.length() > 16L * 1024 * 1024) emptyList() else GpsSpatialModel.savedFixes(JSONObject(file.readText()))
                    val details = fixes.mapIndexed { index, fix -> "${index + 1}. Receipt ${fix.receivedUtc ?: "unknown"} · ${fixDescription(fix, false)}" }
                    SavedLocations(fixes, null, (listOf("${fixes.size} valid fix(es) from the last phone capture.") + details).joinToString("\n"))
                }
            }
            handler.post {
                if (isFinishing || isDestroyed) return@post
                loaded.fold(onSuccess = { data ->
                    saved = data.fixes; plot.setSavedLabels(data.labels); plot.setFixes(saved, live)
                    basemap.setSavedLabels(data.labels); basemap.setFixes(saved, live)
                    if (basemapEnabled) basemap.fitToPoints()
                    savedInfo.text = data.description
                }, onFailure = { savedInfo.text = "Saved locations are unavailable. The original capture or survey remains unchanged." })
            }
        }.apply { name = "Veilbreaker saved location reader"; start() }
    }

    private fun beginLive() {
        if (!visible) return
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION), 46); return
        }
        try { location.start(true); started = true; liveButton.text = "Stop live GPS"; handler.post(tick) }
        catch (_: RuntimeException) { status.text = "GPS provider unavailable. Saved points remain available." }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 46) {
            if (visible && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED) beginLive()
            else status.text = "Precise location permission is unavailable; saved points remain available."
        }
    }

    private fun stopLive() {
        started = false; handler.removeCallbacks(tick); location.stop(); live = null
        plot.setFixes(saved, null); liveButton.text = "Start live GPS"
        basemap.setFixes(saved, null)
        status.text = "Live GPS stopped. Saved locations remain available."
    }

    override fun onStart() { super.onStart(); visible = true }
    override fun onStop() { visible = false; cancelMapLoad(); stopLive(); if (basemapEnabled) showCoordinatePlot(); super.onStop() }

    private fun showCoordinatePlot() {
        basemapEnabled = false
        basemap.setActive(false)
        basemap.visibility = View.GONE
        plot.visibility = View.VISIBLE
        mapInfo.text = if (imageSource.isNotEmpty()) "Operator image: $imageSource · bounds and orientation are unverified." else "Coordinate plot only; no geographic basemap."
    }

    @Deprecated("The document picker returns a temporary read grant for the selected image")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != 45 || resultCode != RESULT_OK || data?.data == null) return
        val bounds = pendingBounds ?: return
        cancelMapLoad()
        val load = MapLoad(data.data!!, bounds, pendingSource)
        imageLoad = load
        status.text = "Loading local image…"
        load.thread = Thread {
            val result = runCatching { readImage(load) }
            handler.post {
                if (imageLoad !== load || load.cancelled || !visible || isFinishing || isDestroyed) {
                    result.getOrNull()?.recycle()
                } else {
                    imageLoad = null
                    result.fold(onSuccess = { bitmap ->
                        showCoordinatePlot()
                        plot.setImage(bitmap, bounds); imageSource = load.source
                        mapInfo.text = "Operator image: $imageSource · WGS84 Plate Carrée bounds ${bounds.west}, ${bounds.south}, ${bounds.east}, ${bounds.north} are unverified. Only fixes inside the bounds appear on the image."
                        status.text = "Image loaded. Live GPS remains off until started."
                    }, onFailure = { error ->
                        status.text = "Cannot open map image: ${error.message ?: "unsupported or unavailable"}. Existing image is unchanged."
                    })
                }
            }
        }.apply { name = "Veilbreaker local map import"; start() }
    }

    private fun cancelMapLoad() {
        val load = imageLoad ?: return
        imageLoad = null; load.cancelled = true
        load.thread?.interrupt()
        // A document provider can block during close as well as read. Never wait
        // for it on the activity thread while the user leaves the screen.
        val stream = load.stream
        if (stream != null) Thread {
            try { stream.close() } catch (_: Exception) { }
        }.apply { name = "Veilbreaker map stream close"; isDaemon = true; start() }
    }

    private fun readImage(load: MapLoad): Bitmap {
        val maxBytes = 20 * 1024 * 1024
        val bytes = contentResolver.openInputStream(load.uri)?.use { input ->
            load.stream = input
            check(!load.cancelled) { "Image loading cancelled." }
            val output = ByteArrayOutputStream(); val buffer = ByteArray(65536); var total = 0; var emptyReads = 0
            while (true) {
                check(!load.cancelled && !Thread.currentThread().isInterrupted) { "Image loading cancelled." }
                val count = input.read(buffer); if (count < 0) break
                if (count == 0) { require(++emptyReads < 20) { "Image provider returned no data." }; continue }
                emptyReads = 0
                total += count; require(total <= maxBytes) { "Image exceeds 20 MiB." }; output.write(buffer, 0, count)
            }
            output.toByteArray()
        } ?: throw IllegalArgumentException("Image access unavailable.")
        load.stream = null
        check(!load.cancelled) { "Image loading cancelled." }
        val probe = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeByteArray(bytes, 0, bytes.size, probe)
        require(probe.outMimeType == "image/png" || probe.outMimeType == "image/jpeg") { "Choose a JPEG or PNG image." }
        val sample = GpsSpatialModel.imageSampleSize(probe.outWidth, probe.outHeight) ?: throw IllegalArgumentException("Image dimensions exceed the limit.")
        val orientation = try { ExifInterface(ByteArrayInputStream(bytes)).getAttribute(ExifInterface.TAG_ORIENTATION) }
            catch (_: Exception) { throw IllegalArgumentException("Image orientation metadata cannot be read safely.") }
        require(GpsSpatialModel.isMapOrientationSafe(orientation)) { "Rotated, mirrored or unknown EXIF orientation is not supported; save a north-up image with normal orientation." }
        check(!load.cancelled) { "Image loading cancelled." }
        return BitmapFactory.decodeByteArray(bytes, 0, bytes.size, BitmapFactory.Options().apply { inSampleSize = sample })
            ?: throw IllegalArgumentException("Image cannot be decoded.")
    }

    private fun liveDescription(fix: GpsSpatialModel.Fix) = "Live GPS · " + fixDescription(fix, true)
    private fun fixDescription(fix: GpsSpatialModel.Fix, isLive: Boolean): String {
        val whenAge = fix.ageAtReceiptMs?.let { "${it / 1000}s " + if (isLive) "old now" else "old at receipt" } ?: "age unavailable"
        return String.format(Locale.US, "%.6f, %.6f · ±%.0f m · %s · %s%s", fix.latitude, fix.longitude, fix.accuracy,
            fix.provider ?: "provider unknown", whenAge, if (fix.mock) " · mock location" else "")
    }
}

/** Local image overlay, or a clearly labeled coordinate plot when no image is chosen. */
class GpsPlotView(context: Context) : View(context) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    private var image: Bitmap? = null
    private var extent: GpsSpatialModel.Bounds? = null
    private var saved: List<GpsSpatialModel.Fix> = emptyList()
    private var savedLabels: List<String>? = null
    private var live: GpsSpatialModel.Fix? = null
    init { contentDescription = "GPS map or coordinate plot; saved and live positions are also described in text." }

    fun setImage(value: Bitmap?, bounds: GpsSpatialModel.Bounds?) { image = value; extent = bounds; invalidate() }
    fun setSavedLabels(labels: List<String>?) { savedLabels = labels; invalidate() }
    fun setFixes(values: List<GpsSpatialModel.Fix>, current: GpsSpatialModel.Fix?) { saved = values; live = current; invalidate() }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val w = width.toFloat(); val h = height.toFloat()
        paint.color = Color.rgb(12, 23, 36); canvas.drawRect(0f, 0f, w, h, paint)
        val all = saved + listOfNotNull(live)
        var bounds = extent
        val bitmap = image
        var box = RectF(12f, 12f, w - 12f, h - 12f)
        if (bitmap != null && bounds != null) {
            val scale = min(box.width() / bitmap.width, box.height() / bitmap.height)
            val bw = bitmap.width * scale; val bh = bitmap.height * scale
            box = RectF((w - bw) / 2, (h - bh) / 2, (w + bw) / 2, (h + bh) / 2)
            paint.color = Color.WHITE; canvas.drawBitmap(bitmap, null, box, paint)
        } else {
            paint.color = Color.rgb(40, 59, 75); paint.strokeWidth = 1f
            for (i in 1..3) { canvas.drawLine(box.left + box.width()*i/4, box.top, box.left + box.width()*i/4, box.bottom, paint); canvas.drawLine(box.left, box.top + box.height()*i/4, box.right, box.top + box.height()*i/4, paint) }
            if (all.isNotEmpty()) {
                val west = all.minOf { it.longitude }; val east = all.maxOf { it.longitude }
                val south = all.minOf { it.latitude }; val north = all.maxOf { it.latitude }
                if (east - west <= 180) bounds = GpsSpatialModel.bounds(max(-180.0, west - 0.0005), max(-90.0, south - 0.0005), min(180.0, east + 0.0005), min(90.0, north + 0.0005))
            }
        }
        if (bounds != null) {
            canvas.save(); canvas.clipRect(box)
            for ((index, fix) in all.withIndex()) {
                val point = GpsSpatialModel.mapPoint(bounds, fix.latitude, fix.longitude) ?: continue
                val x = box.left + (point.first * box.width()).toFloat(); val y = box.top + (point.second * box.height()).toFloat()
                val color = if (fix === live) Color.rgb(89, 220, 201) else Color.rgb(190, 139, 244)
                val latitudeScale = 111320.0
                val longitudeScale = latitudeScale * abs(cos(Math.toRadians(fix.latitude)))
                if (longitudeScale > 1 && fix.accuracy > 0) {
                    val rx = min((fix.accuracy / longitudeScale / (bounds.east - bounds.west) * box.width()).toFloat(), w * 8)
                    val ry = min((fix.accuracy / latitudeScale / (bounds.north - bounds.south) * box.height()).toFloat(), h * 8)
                    paint.color = color; paint.alpha = 80; paint.style = Paint.Style.STROKE; paint.strokeWidth = 2f
                    canvas.drawOval(x-rx,y-ry,x+rx,y+ry,paint); paint.style = Paint.Style.FILL; paint.alpha = 255
                }
                paint.color = color; canvas.drawCircle(x, y, 6f * resources.displayMetrics.density, paint)
                val label = if (index < saved.size) savedLabels?.getOrNull(index) else null
                if (label != null) {
                    paint.color = Color.WHITE; paint.textSize = 12f * resources.displayMetrics.scaledDensity
                    canvas.drawText(label, x + 8f * resources.displayMetrics.density, y - 8f * resources.displayMetrics.density, paint)
                }
            }
            canvas.restore()
        }
        paint.color = Color.WHITE; paint.textSize = 12f * resources.displayMetrics.scaledDensity
        canvas.drawText(if (bitmap == null) "COORDINATE PLOT · NO BASEMAP" else "OPERATOR IMAGE · APPROXIMATE", 16f, 20f * resources.displayMetrics.scaledDensity, paint)
    }
}
