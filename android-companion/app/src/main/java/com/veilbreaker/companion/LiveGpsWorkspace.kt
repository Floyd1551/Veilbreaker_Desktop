package com.veilbreaker.companion

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.location.GnssStatus
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale

/** User-started, foreground-only receiver status; this view never stores location evidence. */
class LiveGpsWorkspace(context: Context) : LinearLayout(context) {
    private val manager = context.getSystemService(LocationManager::class.java)
    private val handler = Handler(Looper.getMainLooper())
    private val action = Button(context)
    private val status = TextView(context)
    private val satellites = TextView(context)
    private val satelliteToggle = Button(context)
    private var running = false
    private var epoch = 0
    private var locationListener: LocationListener? = null
    private var gnssCallback: GnssStatus.Callback? = null
    private var lastFix: Location? = null
    private var satelliteRows: List<LiveGpsSummary.Satellite>? = null
    private var lastSatelliteReceipt: Long? = null
    private var expanded = false
    private var gnssAvailable = true
    private val tick = object : Runnable {
        override fun run() {
            if (!running) return
            render()
            handler.postDelayed(this, 1000)
        }
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    init {
        orientation = VERTICAL
        addView(TextView(context).apply {
            text = "LIVE GPS / SATELLITES"; textSize = 12f; setTypeface(null, Typeface.BOLD)
            setTextColor(Color.parseColor("#83cde3")); setPadding(0, dp(8), 0, dp(4))
        })
        addView(TextView(context).apply {
            text = "Start an on-screen receiver view. Live readings are not saved and stop when you leave."
            textSize = 12f; setTextColor(Color.parseColor("#b8cbd9"))
        })
        action.apply {
            text = "Start live GPS"; styleFieldButton(); setOnClickListener { if (running) stop() else start() }
        }
        addView(action)
        status.apply {
            text = "Live GPS off. Start to see current position and satellites."; textSize = 13f
            setTextColor(Color.parseColor("#e0edf5")); setPadding(0, dp(6), 0, dp(4))
        }
        addView(status)
        satelliteToggle.apply {
            text = "Show satellite details"; styleFieldButton(); visibility = View.GONE
            setOnClickListener { expanded = !expanded; render() }
        }
        addView(satelliteToggle)
        satellites.apply {
            textSize = 12f; setTextColor(Color.parseColor("#b8cbd9")); setTextIsSelectable(true)
            setPadding(0, dp(4), 0, dp(6)); visibility = View.GONE
        }
        addView(satellites)
    }

    private fun constellation(value: Int) = when (value) {
        GnssStatus.CONSTELLATION_GPS -> "GPS"
        GnssStatus.CONSTELLATION_GLONASS -> "GLONASS"
        GnssStatus.CONSTELLATION_GALILEO -> "Galileo"
        GnssStatus.CONSTELLATION_BEIDOU -> "BeiDou"
        GnssStatus.CONSTELLATION_QZSS -> "QZSS"
        GnssStatus.CONSTELLATION_SBAS -> "SBAS"
        GnssStatus.CONSTELLATION_IRNSS -> "NavIC"
        else -> "Unknown"
    }

    @SuppressLint("MissingPermission")
    private fun start() {
        if (!isShown || !isAttachedToWindow) return
        if (context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            status.text = "Precise location permission is required. Grant it in Configure cellular & GPS."
            return
        }
        val receiver = manager
        if (receiver == null || !runCatching { receiver.isLocationEnabled && receiver.isProviderEnabled(LocationManager.GPS_PROVIDER) }.getOrDefault(false)) {
            status.text = "GPS is unavailable or location services are off."
            return
        }
        val token = ++epoch
        val listener = object : LocationListener {
            override fun onLocationChanged(location: Location) {
                if (running && epoch == token) { lastFix = Location(location); render() }
            }
            override fun onProviderDisabled(provider: String) {
                if (running && epoch == token) stop("GPS provider stopped. Live readings are no longer available.")
            }
            override fun onProviderEnabled(provider: String) {}
            @Deprecated("Platform callback") override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) {}
        }
        val callback = object : GnssStatus.Callback() {
            override fun onSatelliteStatusChanged(value: GnssStatus) {
                if (!running || epoch != token) return
                satelliteRows = (0 until value.satelliteCount.coerceAtMost(256)).map { i ->
                    LiveGpsSummary.Satellite(constellation(value.getConstellationType(i)), value.getSvid(i),
                        value.usedInFix(i), value.getCn0DbHz(i), value.getElevationDegrees(i), value.getAzimuthDegrees(i))
                }
                lastSatelliteReceipt = SystemClock.elapsedRealtime()
                render()
            }
        }
        try {
            running = true; lastFix = null; satelliteRows = null; lastSatelliteReceipt = null
            locationListener = listener
            receiver.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000L, 0f, listener, Looper.getMainLooper())
            gnssAvailable = receiver.registerGnssStatusCallback(callback, handler)
            if (gnssAvailable) gnssCallback = callback
            action.text = "Stop live GPS"
            handler.post(tick)
        } catch (_: SecurityException) {
            stop("Precise location permission is unavailable. Grant it in Configure cellular & GPS.")
        } catch (_: IllegalArgumentException) {
            stop("GPS provider is unavailable on this device.")
        } catch (_: RuntimeException) {
            stop("Live GPS could not be started on this device.")
        }
    }

    private fun render() {
        if (!running) return
        val now = SystemClock.elapsedRealtime()
        val fix = lastFix
        val position = if (fix == null) "Waiting for a GPS fix." else {
            val age = (now - fix.elapsedRealtimeNanos / 1_000_000).coerceAtLeast(0)
            val accuracy = if (fix.hasAccuracy()) String.format(Locale.US, "±%.1f m", fix.accuracy) else "not exposed"
            val extra = listOfNotNull(
                if (fix.hasAltitude()) String.format(Locale.US, "Altitude %.1f m (ellipsoid)", fix.altitude) else null,
                if (fix.hasSpeed()) String.format(Locale.US, "Speed %.1f m/s", fix.speed) else null,
                if (fix.hasBearing()) String.format(Locale.US, "Bearing %.0f°", fix.bearing) else null)
            String.format(Locale.US, "Position %.6f, %.6f · accuracy %s\nFix age %.1f s · %s%s",
                fix.latitude, fix.longitude, accuracy, age / 1000.0, fix.provider ?: "GPS",
                if (extra.isEmpty()) "" else "\n" + extra.joinToString(" · ")) +
                if (fix.isFromMockProvider) "\nMock location reported by Android." else ""
        }
        val counts = if (!gnssAvailable) "Satellite status unavailable." else if (satelliteRows == null) "Waiting for satellite status."
            else "${satelliteRows!!.size} satellites reported · ${satelliteRows!!.count { it.used }} used in last fix"
        val satelliteAge = lastSatelliteReceipt?.let { " · status received ${(now - it).coerceAtLeast(0) / 1000} s ago" } ?: ""
        status.text = "$position\n$counts$satelliteAge\nSatellite use and signal strength are Android reports, not saved evidence."
        satelliteToggle.visibility = if (satelliteRows != null) View.VISIBLE else View.GONE
        satelliteToggle.text = if (expanded) "Hide satellite details" else "Show satellite details"
        satelliteToggle.isSelected = expanded
        satellites.visibility = if (expanded && satelliteRows != null) View.VISIBLE else View.GONE
        if (expanded) satellites.text = LiveGpsSummary.satellites(satelliteRows)
    }

    private fun stop(message: String = "Live GPS stopped. Readings were not saved.") {
        epoch++; running = false; handler.removeCallbacks(tick)
        val receiver = manager
        try { locationListener?.let { receiver?.removeUpdates(it) } } catch (_: RuntimeException) {}
        try { gnssCallback?.let { receiver?.unregisterGnssStatusCallback(it) } } catch (_: RuntimeException) {}
        locationListener = null; gnssCallback = null; lastFix = null; satelliteRows = null; lastSatelliteReceipt = null
        action.text = "Start live GPS"; status.text = message
        satelliteToggle.visibility = View.GONE; satellites.visibility = View.GONE; expanded = false
    }

    override fun onDetachedFromWindow() { if (running) stop(); super.onDetachedFromWindow() }
    override fun onWindowVisibilityChanged(visibility: Int) {
        super.onWindowVisibilityChanged(visibility)
        if (visibility != View.VISIBLE && running) stop()
    }
    override fun onVisibilityChanged(changedView: View, visibility: Int) {
        super.onVisibilityChanged(changedView, visibility)
        if (visibility != View.VISIBLE && running) stop()
    }
}
