package com.veilbreaker.companion

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.graphics.Color
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
    private var wifiChecked: TextView? = null
    private var wifiText = "Wi-Fi status not yet checked."
    private var wifiCheckedText = ""
    private val wifiHandler = Handler(Looper.getMainLooper())
    private val wifiInfo = mutableMapOf<Network, WifiInfo>()
    private var wifiCallback: ConnectivityManager.NetworkCallback? = null
    private var wifiPermissionAtRegistration = false
    private var wifiEpoch = 0
    private var redrawPending = false
    private val redrawWifi = Runnable { redrawPending = false; updateWifiSummary() }

    init { orientation = VERTICAL }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun color(value: String) = Color.parseColor(value)

    private fun text(parent: LinearLayout, value: String, size: Float = 13f, tone: String = "#b8cbd9", bold: Boolean = false): TextView =
        TextView(context).apply {
            text = value; textSize = size; setTextColor(color(tone)); setPadding(0, dp(1), 0, dp(1))
            if (bold) setTypeface(null, Typeface.BOLD)
            parent.addView(this)
        }

    private fun surface(fill: String, border: String, radius: Int = 10) = GradientDrawable().apply {
        setColor(color(fill)); setStroke(dp(1), color(border)); cornerRadius = dp(radius).toFloat()
    }

    private fun panel(title: String): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL; setPadding(dp(14), dp(12), dp(14), dp(12))
        background = surface("#101e2c", "#294052")
        this@LiveDashboard.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        text(this, title, 12f, "#83cde3", true).apply { letterSpacing = 0.06f }
    }

    // A saved capture is separate from the current network state. Do not imply that
    // these values are live measurements or assign a quality grade to them.
    private fun cellPanel(parent: LinearLayout): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL; setPadding(dp(12), dp(10), dp(12), dp(10))
        background = surface("#142737", "#304a5c", 8)
        parent.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
    }

    private fun stackedLayout() = resources.configuration.screenWidthDp < 360 || resources.configuration.fontScale > 1.15f

    private fun displayValue(value: LiveOverviewModel.Value): String {
        val raw = value.value ?: return "Not exposed"
        val number = if (raw == raw.toLong().toDouble()) raw.toLong().toString() else String.format(Locale.US, "%.1f", raw)
        return "$number ${value.unit}"
    }

    private fun metric(parent: LinearLayout, value: LiveOverviewModel.Value) {
        val metric = LinearLayout(context).apply {
            orientation = VERTICAL; setPadding(dp(8), dp(6), dp(6), dp(6))
            background = surface("#0d1c29", "#294152", 6)
            parent.addView(this, if (parent.orientation == HORIZONTAL) LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f).apply {
                marginEnd = dp(4)
            } else LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(4) })
        }
        text(metric, value.label, 11f, "#a8c2d1", true)
        text(metric, displayValue(value), if (value.value == null) 12f else 16f,
            if (value.value == null) "#a8bdca" else "#f2f8fc", value.value != null)
    }

    private fun action(parent: LinearLayout, title: String, action: () -> Unit): Button =
        Button(context).apply {
            text = title; isAllCaps = false; minHeight = dp(48); gravity = Gravity.CENTER
            val states = arrayOf(intArrayOf(-android.R.attr.state_enabled), intArrayOf())
            backgroundTintList = ColorStateList(states, intArrayOf(color("#1b2935"), color("#254e7f")))
            setTextColor(ColorStateList(states, intArrayOf(color("#8ca0ae"), color("#ffffff"))))
            setOnClickListener { action() }; isEnabled = navigationEnabled
            parent.addView(this, if (parent.orientation == HORIZONTAL) LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f).apply {
                marginEnd = dp(4)
            } else LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        }

    fun setNavigationEnabled(enabled: Boolean) {
        navigationEnabled = enabled; wifiButton?.isEnabled = enabled; gpsButton?.isEnabled = enabled
        navigationStatus?.visibility = if (enabled) View.GONE else View.VISIBLE
    }

    fun showCapture(capture: JSONObject?, plan: JSONObject?) {
        removeAllViews(); wifiButton = null; gpsButton = null; navigationStatus = null; wifiSummary = null; wifiChecked = null
        val model = runCatching { LiveOverviewModel.build(capture, plan) }.getOrElse { LiveOverviewModel.Overview(null, emptyList(), null) }
        val overview = panel("CELLULAR  /  LATEST CAPTURE")
        text(overview, model.receivedUtc?.let { "Received $it · sample ages at receipt" }
            ?: "No recorded phone capture yet. Select Capture to collect.", 12f, "#9ab3c3")
        if (model.cells.isEmpty()) text(overview, "No registered LTE or NR cells in the latest capture.", 13f)
        for (cell in model.cells) {
            val card = cellPanel(overview)
            text(card, cell.title, 15f, "#f2f8fc", true)
            text(card, "${cell.carrier} · ${cell.band}", 13f, "#91d9ed")
            text(card, "Channel ${cell.channel} · PCI ${cell.pci}", 12f, "#b8cbd9")
            val metrics = LinearLayout(context).apply {
                orientation = if (stackedLayout()) VERTICAL else HORIZONTAL
                card.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
            }
            cell.values.forEach { metric(metrics, it) }
            text(card, cell.age, 11f, "#a8bfcd").apply { setPadding(0, dp(6), 0, 0) }
            if (cell.receivedUtc != null && cell.receivedUtc != model.receivedUtc)
                text(card, "Received ${cell.receivedUtc}", 11f, "#a8bfcd")
        }
        val wifi = panel("WI-FI  /  CURRENT STATUS")
        wifiSummary = text(wifi, wifiText, 13f, "#e0edf5").apply {
            setPadding(0, dp(6), 0, dp(4)); setLineSpacing(dp(2).toFloat(), 1f)
        }
        wifiChecked = text(wifi, wifiCheckedText, 11f, "#a8bfcd").apply {
            visibility = if (wifiCheckedText.isEmpty()) View.GONE else View.VISIBLE
        }
        wifiButton = action(wifi, "Open Wi-Fi", onWifi)

        val gps = panel("GPS  /  LATEST CAPTURE")
        text(gps, model.gps ?: "No location in the latest saved capture.", 13f, "#e0edf5").apply {
            setPadding(0, dp(6), 0, dp(4))
        }
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
        wifiEpoch++; wifiHandler.removeCallbacks(redrawWifi); redrawPending = false; wifiInfo.clear()
        val existing = wifiCallback; wifiCallback = null
        if (existing != null) try { context.getSystemService(ConnectivityManager::class.java)?.unregisterNetworkCallback(existing) }
            catch (_: RuntimeException) { }
        wifiText = "Wi-Fi monitor inactive."
        wifiCheckedText = ""
        wifiSummary?.text = wifiText
        wifiChecked?.visibility = View.GONE
    }

    @Suppress("DEPRECATION")
    private fun updateWifiSummary() {
        wifiCheckedText = ""
        val wifi = context.applicationContext.getSystemService(WifiManager::class.java)
        val manager = context.getSystemService(ConnectivityManager::class.java)
        if (wifi == null || manager == null) {
            wifiText = "Android Wi-Fi information unavailable."
        } else {
            try {
                val networks = manager.allNetworks.filter { manager.getNetworkCapabilities(it)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true }
                val active = manager.activeNetwork
                val network = networks.firstOrNull { it == active } ?: networks.firstOrNull()
                // Never borrow legacy connectionInfo for a different selected network.
                val info = network?.let { wifiInfo[it] ?: (manager.getNetworkCapabilities(it)?.transportInfo as? WifiInfo) }
                val permission = context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
                wifiText = LiveWifiSummary.format(wifi.isWifiEnabled, network != null, network != null && network == active,
                    permission, info?.ssid, info?.rssi, info?.frequency, info?.linkSpeed)
                // Combine only adjacent status/name lines; all source and age qualifiers remain visible.
                val firstBreak = wifiText.indexOf('\n')
                if (firstBreak >= 0) wifiText = wifiText.replaceRange(firstBreak, firstBreak + 1, " · ")
                wifiCheckedText = "Checked " + DateFormat.getTimeInstance(DateFormat.MEDIUM).format(Date())
            } catch (_: RuntimeException) { wifiText = "Android did not expose Wi-Fi connection information." }
        }
        wifiSummary?.text = wifiText
        wifiChecked?.apply { text = wifiCheckedText; visibility = if (wifiCheckedText.isEmpty()) View.GONE else View.VISIBLE }
    }
}
