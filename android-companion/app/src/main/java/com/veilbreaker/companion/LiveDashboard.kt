package com.veilbreaker.companion

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject
import java.text.DateFormat
import java.util.Date
import java.util.Locale

/** Field dashboard of existing evidence; it never starts or modifies a capture. */
class LiveDashboard(context: Context, private val onWifi: () -> Unit, private val onGps: () -> Unit) : LinearLayout(context) {
    private var navigationEnabled = true
    private var wifiButton: Button? = null
    private var gpsButton: Button? = null
    private var navigationStatus: TextView? = null
    private var wifiSummary: TextView? = null
    private var wifiName: TextView? = null
    private var wifiFrequency: TextView? = null
    private val wifiValues = mutableListOf<TextView>()
    private var wifiChecked: TextView? = null
    private var wifiDetails = LiveWifiSummary.details(false, false, false, false, null, null, null, null)
    private var wifiCheckedText = ""
    private val wifiHandler = Handler(Looper.getMainLooper())
    private val wifiInfo = mutableMapOf<Network, WifiInfo>()
    private var wifiCallback: ConnectivityManager.NetworkCallback? = null
    private var wifiPermissionAtRegistration = false
    private var wifiEpoch = 0
    private var redrawPending = false
    private val redrawWifi = Runnable { redrawPending = false; updateWifiSummary() }
    private val wifiPoll = object : Runnable {
        override fun run() {
            if (wifiCallback == null || !isShown || windowVisibility != View.VISIBLE) return
            updateWifiSummary()
            wifiHandler.postDelayed(this, 3000)
        }
    }

    init { orientation = VERTICAL }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun color(value: String) = Color.parseColor(value)

    private fun text(parent: LinearLayout, value: String, size: Float = 13f, tone: String = "#b4c8d1", bold: Boolean = false): TextView =
        TextView(context).apply {
            text = value; textSize = size; setTextColor(color(tone)); setPadding(0, dp(1), 0, dp(1))
            if (bold) setTypeface(null, Typeface.BOLD)
            parent.addView(this)
        }

    private fun surface(fill: String, radius: Int = 16) = GradientDrawable().apply {
        setColor(color(fill)); cornerRadius = dp(radius).toFloat()
    }

    /** Decorative section icon; measurement values remain in accessible text. */
    private class SectionIcon(context: Context, private val kind: String, private val accent: Int) : View(context) {
        private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply {
            color = accent; style = Paint.Style.STROKE; strokeWidth = 1.7f
            strokeCap = Paint.Cap.ROUND; strokeJoin = Paint.Join.ROUND
        }
        private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = accent; alpha = 28 }
        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            val scale = minOf(width, height) / 36f
            canvas.save(); canvas.scale(scale, scale)
            canvas.drawCircle(18f, 18f, 18f, fill)
            when (kind) {
                "cellular" -> {
                    canvas.drawLine(11f, 23f, 11f, 20f, stroke)
                    canvas.drawLine(15.5f, 23f, 15.5f, 17f, stroke)
                    canvas.drawLine(20f, 23f, 20f, 14f, stroke)
                    canvas.drawLine(24.5f, 23f, 24.5f, 10.5f, stroke)
                }
                "wifi" -> {
                    canvas.drawArc(8f, 9f, 28f, 29f, 225f, 90f, false, stroke)
                    canvas.drawArc(12f, 13f, 24f, 25f, 225f, 90f, false, stroke)
                    canvas.drawPoint(18f, 22f, stroke)
                }
                else -> {
                    val pin = Path().apply {
                        moveTo(18f, 27f); cubicTo(15.2f, 23.1f, 11.7f, 19.8f, 11.7f, 16.1f)
                        cubicTo(11.7f, 12.6f, 14.5f, 9.8f, 18f, 9.8f)
                        cubicTo(21.5f, 9.8f, 24.3f, 12.6f, 24.3f, 16.1f)
                        cubicTo(24.3f, 19.8f, 20.8f, 23.1f, 18f, 27f); close()
                    }
                    canvas.drawPath(pin, stroke); canvas.drawCircle(18f, 16f, 2.1f, stroke)
                }
            }
            canvas.restore()
        }
    }

    private fun panel(title: String, contextLabel: String, kind: String, accent: String): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL; setPadding(dp(16), dp(16), dp(16), dp(16))
        background = surface("#142532", 16)
        this@LiveDashboard.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(12) })
        val header = LinearLayout(context).apply {
            orientation = HORIZONTAL; gravity = Gravity.CENTER_VERTICAL
        }
        addView(header, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        header.addView(SectionIcon(context, kind, color(accent)).apply {
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        }, LayoutParams(dp(36), dp(36)).apply { marginEnd = dp(10) })
        val titles = LinearLayout(context).apply {
            orientation = VERTICAL; header.addView(this, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
        }
        text(titles, title, 17f, "#edf5f8", true)
        text(titles, contextLabel, 12f, "#a7c5d3")
    }

    // A saved capture is separate from the current network state. Do not imply that
    // these values are live measurements or assign a quality grade to them.
    private fun details(parent: LinearLayout): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL
        parent.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(10) })
    }

    private fun stackedLayout() = resources.configuration.screenWidthDp < 360 || resources.configuration.fontScale > 1.15f

    private fun displayValue(value: LiveOverviewModel.Value): String {
        val raw = value.value ?: return "Not exposed"
        val number = if (raw == raw.toLong().toDouble()) raw.toLong().toString() else String.format(Locale.US, "%.1f", raw)
        return "$number ${value.unit}"
    }

    private fun metric(parent: LinearLayout, label: String, value: String, available: Boolean = true): TextView {
        val metric = LinearLayout(context).apply {
            orientation = VERTICAL; setPadding(dp(10), dp(8), dp(8), dp(8))
            background = surface("#10212d", 10)
            parent.addView(this, if (parent.orientation == HORIZONTAL) LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f).apply {
                marginEnd = dp(4)
            } else LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(4) })
        }
        val reading = text(metric, value, if (available) 16f else 12f,
            if (available) "#edf5f8" else "#a8bdca", available)
        text(metric, label, 12f, "#aec6d3")
        return reading
    }

    private fun action(parent: LinearLayout, title: String, action: () -> Unit): Button =
        Button(context).apply {
            text = title; styleFieldButton(); gravity = Gravity.CENTER
            setOnClickListener { action() }; isEnabled = navigationEnabled
            parent.addView(this, if (parent.orientation == HORIZONTAL) LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f).apply {
                marginEnd = dp(4)
            } else LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        }

    fun setNavigationEnabled(enabled: Boolean) {
        navigationEnabled = enabled; wifiButton?.isEnabled = enabled; gpsButton?.isEnabled = enabled
        navigationStatus?.visibility = if (enabled) View.GONE else View.VISIBLE
    }

    fun showCapture(capture: JSONObject?, plan: JSONObject?) {
        removeAllViews(); wifiButton = null; gpsButton = null; navigationStatus = null; wifiSummary = null; wifiName = null; wifiFrequency = null; wifiValues.clear(); wifiChecked = null
        val model = runCatching { LiveOverviewModel.build(capture, plan) }.getOrElse { LiveOverviewModel.Overview(null, emptyList(), null) }
        val overview = panel("Cellular", "Latest saved capture", "cellular", "#86baff")
        text(overview, model.receivedUtc?.let { "Received $it · sample ages at receipt" }
            ?: "No recorded phone capture yet. Select Capture to collect.", 12f, "#a7c0cc").apply { setPadding(0, dp(10), 0, dp(2)) }
        if (model.cells.isEmpty()) text(overview, "No registered LTE or NR cells in the latest capture.", 13f)
        for ((index, cell) in model.cells.withIndex()) {
            if (index > 0) overview.addView(View(context).apply { setBackgroundColor(color("#2b424e")) },
                LayoutParams(LayoutParams.MATCH_PARENT, dp(1)).apply { topMargin = dp(12) })
            val card = details(overview)
            text(card, cell.title, 15f, "#edf5f8", true)
            text(card, "${cell.carrier} · ${cell.band}", 13f, "#78d8db")
            text(card, "Channel ${cell.channel} · PCI ${cell.pci}", 12f, "#b4c8d1")
            val metrics = LinearLayout(context).apply {
                orientation = if (stackedLayout()) VERTICAL else HORIZONTAL
                card.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
            }
            cell.values.forEach { metric(metrics, it.label, displayValue(it), it.value != null) }
            text(card, cell.age, 11f, "#a8bfcd").apply { setPadding(0, dp(6), 0, 0) }
            if (cell.receivedUtc != null && cell.receivedUtc != model.receivedUtc)
                text(card, "Received ${cell.receivedUtc}", 11f, "#a8bfcd")
        }
        val wifi = panel("Wi-Fi", "Current connection", "wifi", "#78d8db")
        val wifiCard = details(wifi)
        wifiSummary = text(wifiCard, wifiDetails.status, 15f, "#edf5f8", true)
        wifiName = text(wifiCard, wifiDetails.name, 13f, "#78d8db")
        wifiFrequency = text(wifiCard, "Frequency ${wifiDetails.frequency}", 12f, "#b4c8d1")
        val wifiMetrics = LinearLayout(context).apply {
            orientation = if (stackedLayout()) VERTICAL else HORIZONTAL
            wifiCard.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        }
        for ((label, value) in listOf("Signal" to wifiDetails.signal, "Channel" to wifiDetails.channel, "Link rate" to wifiDetails.linkRate)) {
            wifiValues.add(metric(wifiMetrics, label, value))
        }
        text(wifiCard, "Channel is derived from frequency. Link rate is negotiated, not measured throughput; sample age is not exposed.", 12f, "#b4c9d4").apply { setPadding(0, dp(8), 0, 0) }
        wifiChecked = text(wifi, wifiCheckedText, 11f, "#a8bfcd").apply {
            visibility = if (wifiCheckedText.isEmpty()) View.GONE else View.VISIBLE
        }
        wifiButton = action(wifi, "Open Wi-Fi", onWifi)

        val gps = panel("Location", "Latest saved capture and live GPS", "location", "#c0b5ff")
        text(gps, model.gps ?: "No location in the latest saved capture.", 13f, "#e0edf5").apply {
            setPadding(0, dp(6), 0, dp(4))
        }
        gps.addView(LiveGpsWorkspace(context))
        gpsButton = action(gps, "Open GPS & map", onGps)
        navigationStatus = text(gps, "Stop the current capture or desktop connection to open these views.", 12f, "#d2bd91").apply {
            visibility = if (navigationEnabled) View.GONE else View.VISIBLE
        }
        if (isAttachedToWindow) syncWifiMonitor()
    }

    override fun onAttachedToWindow() { super.onAttachedToWindow(); syncWifiMonitor() }
    override fun onDetachedFromWindow() { stopWifiMonitor(); super.onDetachedFromWindow() }
    override fun onWindowVisibilityChanged(visibility: Int) { super.onWindowVisibilityChanged(visibility); if (isAttachedToWindow) syncWifiMonitor() }
    override fun onVisibilityChanged(changedView: View, visibility: Int) { super.onVisibilityChanged(changedView, visibility); if (isAttachedToWindow) syncWifiMonitor() }

    /** Refresh after a permission decision without recording location. */
    fun refreshWifi() { if (isAttachedToWindow) syncWifiMonitor() }

    /** Phone location permission enables Wi-Fi identity access but does not record GPS coordinates. */
    private fun syncWifiMonitor() {
        if (!isAttachedToWindow || !isShown || windowVisibility != View.VISIBLE) { stopWifiMonitor(); return }
        val permission = context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        if (wifiCallback != null && wifiPermissionAtRegistration == permission) { updateWifiSummary(); return }
        if (wifiCallback != null) stopWifiMonitor()
        updateWifiSummary()
        val manager = context.getSystemService(ConnectivityManager::class.java) ?: return
        val epoch = ++wifiEpoch
        val callback = if (Build.VERSION.SDK_INT >= 31) callbackWithLocation(epoch) else callback(epoch)
        try {
            manager.registerNetworkCallback(NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_WIFI).build(), callback)
            wifiCallback = callback; wifiPermissionAtRegistration = permission
            wifiHandler.removeCallbacks(wifiPoll); wifiHandler.post(wifiPoll)
        } catch (_: RuntimeException) { wifiCallback = null }
    }

    private fun callback(epoch: Int) = object : ConnectivityManager.NetworkCallback() {
        override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) = onWifiCapabilities(network, capabilities, epoch)
        override fun onLost(network: Network) = onWifiLost(network, epoch)
    }
    private fun callbackWithLocation(epoch: Int) = object : ConnectivityManager.NetworkCallback(ConnectivityManager.NetworkCallback.FLAG_INCLUDE_LOCATION_INFO) {
        override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) = onWifiCapabilities(network, capabilities, epoch)
        override fun onLost(network: Network) = onWifiLost(network, epoch)
    }
    private fun onWifiCapabilities(network: Network, capabilities: NetworkCapabilities, epoch: Int) {
        val info = capabilities.transportInfo as? WifiInfo
        wifiHandler.post {
            if (wifiEpoch == epoch && wifiCallback != null) {
                if (info == null) wifiInfo.remove(network) else wifiInfo[network] = info
                scheduleWifiRedraw()
            }
        }
    }
    private fun onWifiLost(network: Network, epoch: Int) {
        wifiHandler.post { if (wifiEpoch == epoch && wifiCallback != null) { wifiInfo.remove(network); scheduleWifiRedraw() } }
    }
    private fun scheduleWifiRedraw() {
        if (!redrawPending) { redrawPending = true; wifiHandler.postDelayed(redrawWifi, 300) }
    }
    private fun stopWifiMonitor() {
        wifiEpoch++; wifiHandler.removeCallbacks(redrawWifi); wifiHandler.removeCallbacks(wifiPoll); redrawPending = false; wifiInfo.clear()
        val existing = wifiCallback; wifiCallback = null
        if (existing != null) try { context.getSystemService(ConnectivityManager::class.java)?.unregisterNetworkCallback(existing) }
            catch (_: RuntimeException) { }
        wifiDetails = LiveWifiSummary.details(false, false, false, false, null, null, null, null).copy(status = "Wi-Fi monitor inactive")
        wifiCheckedText = ""
        renderWifi()
        wifiChecked?.visibility = View.GONE
    }

    @Suppress("DEPRECATION")
    private fun updateWifiSummary() {
        wifiCheckedText = ""
        val wifi = context.applicationContext.getSystemService(WifiManager::class.java)
        val manager = context.getSystemService(ConnectivityManager::class.java)
        if (wifi == null || manager == null) {
            wifiDetails = LiveWifiSummary.details(false, false, false, false, null, null, null, null).copy(status = "Android Wi-Fi information unavailable")
        } else {
            try {
                val networks = manager.allNetworks.filter { manager.getNetworkCapabilities(it)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true }
                val active = manager.activeNetwork
                val network = networks.firstOrNull { it == active } ?: networks.firstOrNull()
                // Never borrow legacy connectionInfo for a different selected network.
                val info = network?.let {
                    val fresh = manager.getNetworkCapabilities(it)?.transportInfo as? WifiInfo
                    val callback = wifiInfo[it]
                    if (fresh != null && (WifiSnapshotFormat.ssid(fresh.ssid) != null || callback == null)) fresh else callback
                }
                val permission = context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                wifiDetails = LiveWifiSummary.details(wifi.isWifiEnabled, network != null, network != null && network == active,
                    permission, info?.ssid, info?.rssi, info?.frequency, info?.linkSpeed)
                wifiCheckedText = "Checked " + DateFormat.getTimeInstance(DateFormat.MEDIUM).format(Date())
            } catch (_: RuntimeException) { wifiDetails = LiveWifiSummary.details(false, false, false, false, null, null, null, null).copy(status = "Android did not expose Wi-Fi connection information") }
        }
        renderWifi()
        wifiChecked?.apply { text = wifiCheckedText; visibility = if (wifiCheckedText.isEmpty()) View.GONE else View.VISIBLE }
    }
    private fun renderWifi() {
        wifiSummary?.text = wifiDetails.status
        wifiName?.text = wifiDetails.name
        wifiFrequency?.text = "Frequency ${wifiDetails.frequency}"
        listOf(wifiDetails.signal, wifiDetails.channel, wifiDetails.linkRate).forEachIndexed { i, value -> wifiValues.getOrNull(i)?.text = value }
    }
}
