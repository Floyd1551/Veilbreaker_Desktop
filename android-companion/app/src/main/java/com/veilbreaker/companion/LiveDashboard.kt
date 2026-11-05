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
    private var wifiText = "Wi-Fi status not yet checked."
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

    private fun panel(title: String): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL; setPadding(dp(12), dp(8), dp(12), dp(8))
        background = GradientDrawable().apply {
            setColor(color("#111d2a")); setStroke(dp(1), color("#2a4051")); cornerRadius = dp(8).toFloat()
        }
        this@LiveDashboard.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(6) })
        text(this, title, 14f, "#eaf4fb", true)
    }

    private fun displayValue(value: LiveOverviewModel.Value): String {
        val raw = value.value ?: return "Not exposed"
        val number = if (raw == raw.toLong().toDouble()) raw.toLong().toString() else String.format(Locale.US, "%.1f", raw)
        return "$number ${value.unit}"
    }

    private fun metric(parent: LinearLayout, value: LiveOverviewModel.Value) {
        val metric = LinearLayout(context).apply {
            orientation = VERTICAL; setPadding(0, dp(1), dp(6), dp(1))
            parent.addView(this, if (parent.orientation == HORIZONTAL) LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f)
                else LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        }
        text(metric, value.label, 11f, "#96b2c4")
        text(metric, displayValue(value), 14f, "#f2f8fc", true)
    }

    private fun action(parent: LinearLayout, title: String, action: () -> Unit): Button =
        Button(context).apply {
            text = title; isAllCaps = false; minHeight = dp(48); gravity = Gravity.CENTER
            backgroundTintList = ColorStateList.valueOf(color("#254e7f")); setTextColor(color("#ffffff"))
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
        removeAllViews(); wifiButton = null; gpsButton = null; navigationStatus = null; wifiSummary = null
        val model = runCatching { LiveOverviewModel.build(capture, plan) }.getOrElse { LiveOverviewModel.Overview(null, emptyList(), null) }
        val overview = panel("CELLULAR  /  LATEST CAPTURE")
        text(overview, model.receivedUtc?.let { "Received $it · sample ages at receipt" }
            ?: "No recorded phone capture yet. Select Capture to collect.", 11f, "#96b2c4")
        if (model.cells.isEmpty()) text(overview, "No registered LTE or NR cells in the latest capture.")
        for (cell in model.cells) {
            text(overview, cell.title, 13f, "#eaf4fb", true).apply {
                setPadding(0, dp(5), 0, dp(1))
            }
            text(overview, "${cell.carrier} · ${cell.band}", 12f, "#7ec8f5")
            text(overview, "Channel ${cell.channel} · PCI ${cell.pci}", 12f)
            val metrics = LinearLayout(context).apply {
                orientation = if (resources.configuration.screenWidthDp < 360 || resources.configuration.fontScale > 1.15f) VERTICAL else HORIZONTAL
                overview.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(2) })
            }
            cell.values.forEach { metric(metrics, it) }
            text(overview, cell.age, 11f, "#96b2c4")
            if (cell.receivedUtc != null && cell.receivedUtc != model.receivedUtc)
                text(overview, "Received ${cell.receivedUtc}", 11f, "#96b2c4")
        }
        val connectivity = panel("WI-FI")
        wifiSummary = text(connectivity, wifiText, 12f)
        text(connectivity, "GPS  /  LATEST CAPTURE", 13f, "#eaf4fb", true).apply {
            setPadding(0, dp(6), 0, dp(1))
        }
        text(connectivity, model.gps ?: "No location in the latest saved capture.", 12f)
        val actions = LinearLayout(context).apply {
            orientation = if (resources.configuration.screenWidthDp < 360 || resources.configuration.fontScale > 1.15f) VERTICAL else HORIZONTAL
            connectivity.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(4) })
        }
        wifiButton = action(actions, "Open Wi-Fi", onWifi)
        gpsButton = action(actions, "Open GPS & map", onGps)
        navigationStatus = text(connectivity, "Stop the current capture or desktop connection to open these views.", 11f, "#d2bd91").apply {
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
        wifiSummary?.text = wifiText
    }

    @Suppress("DEPRECATION")
    private fun updateWifiSummary() {
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
                wifiText += " · Checked " + DateFormat.getTimeInstance(DateFormat.MEDIUM).format(Date())
            } catch (_: RuntimeException) { wifiText = "Android did not expose Wi-Fi connection information." }
        }
        wifiSummary?.text = wifiText
    }
}
