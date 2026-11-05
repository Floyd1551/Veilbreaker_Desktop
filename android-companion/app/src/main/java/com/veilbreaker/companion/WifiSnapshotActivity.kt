package com.veilbreaker.companion

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.location.LocationManager
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import java.text.DateFormat
import java.util.Date

/** Foreground, read-only view of platform Wi-Fi observations. No scan is initiated. */
class WifiSnapshotActivity : Activity() {
    private lateinit var results: LinearLayout
    private lateinit var connectedHolder: LinearLayout
    private var visible = false
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private var callbackEpoch = 0
    private val callbackWifi = mutableMapOf<Network, WifiInfo>()
    private val refreshGate = WifiRefreshGate()
    private val mainHandler = Handler(Looper.getMainLooper())
    private var lastPermission = false
    private var lastLocationEnabled = false
    private var lastWifiEnabled = false
    private val redrawConnected = Runnable {
        if (refreshGate.consume() && visible) refreshConnected()
    }
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun color(value: String) = Color.parseColor(value)

    private fun label(parent: LinearLayout, value: String, size: Float = 14f, tone: String = "#b8c9da", bold: Boolean = false): TextView =
        TextView(this).apply {
            text = value; textSize = size; setTextColor(color(tone)); setPadding(0, dp(3), 0, dp(3))
            if (bold) setTypeface(null, Typeface.BOLD)
            parent.addView(this)
        }

    private fun card(parent: LinearLayout, title: String): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL; setPadding(dp(16), dp(12), dp(16), dp(14))
        background = GradientDrawable().apply { setColor(color("#152435")); cornerRadius = dp(12).toFloat(); setStroke(dp(1), color("#294055")) }
        parent.addView(this, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(12) })
        label(this, title, 12f, "#63dec8", true)
    }

    private fun signalMeter(parent: LinearLayout, rssi: Int?) {
        val value = rssi?.takeIf { WifiDisplay.barPercent(it) != null }
        label(parent, value?.let { "$it dBm" } ?: "Signal not exposed", 24f, "#eef7fc", true)
        if (value == null) return
        val meter = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100; progress = WifiDisplay.barPercent(value)!!
            progressTintList = ColorStateList.valueOf(color("#57d7c7"))
            progressBackgroundTintList = ColorStateList.valueOf(color("#34495b"))
            contentDescription = "RSSI $value dBm; display scale minus 120 to minus 30 dBm"
        }
        parent.addView(meter, LinearLayout.LayoutParams(-1, dp(12)).apply { topMargin = dp(4) })
        label(parent, "RSSI scale −120 to −30 dBm · values outside scale are clipped", 11f, "#91a8ba")
    }

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        window.statusBarColor = Color.parseColor("#0d1520")
        window.navigationBarColor = Color.parseColor("#0d1520")
        val scroll = ScrollView(this).apply { setBackgroundColor(Color.parseColor("#0d1520")); isFillViewport = true }
        val content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(20), dp(24), dp(20), dp(24)) }
        scroll.addView(content); setContentView(scroll)
        SystemBarInsets.apply(scroll)
        fun button(value: String, action: () -> Unit) = Button(this).apply {
            this.text = value; isAllCaps = false; minHeight = dp(48)
            backgroundTintList = ColorStateList.valueOf(color("#243b50")); setTextColor(color("#e9f5f9"))
            setOnClickListener { action() }; content.addView(this)
        }
        label(content, "VEILBREAKER  /  WI-FI", 12f, "#63dec8", true)
        label(content, "Wi-Fi environment", 24f, "#eef7fc", true)
        label(content, "Read-only view. Nearby entries are cached Android results, not a new scan. Names and addresses are not saved or exported here.")
        button("Grant Wi-Fi permissions") { requestWifiPermissions() }
        button("Refresh cached results") { refresh() }
        results = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; content.addView(this) }
        button("Back to field workspace") { finish() }
        refresh()
    }

    private fun requestWifiPermissions() {
        requestPermissions(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION), 1)
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == 1) {
            unregisterWifiCallback()
            if (visible) registerWifiCallback()
            refresh()
        }
    }

    override fun onStart() {
        super.onStart()
        visible = true
        refreshGate.start()
        refresh()
        registerWifiCallback()
    }

    override fun onStop() {
        visible = false
        refreshGate.stop()
        mainHandler.removeCallbacks(redrawConnected)
        unregisterWifiCallback()
        callbackWifi.clear()
        super.onStop()
    }

    private fun registerWifiCallback() {
        val manager = getSystemService(ConnectivityManager::class.java) ?: return
        // Android 12+ redacts location-sensitive WifiInfo from synchronous
        // getNetworkCapabilities(); ask for it explicitly in a foreground callback.
        val flags = if (Build.VERSION.SDK_INT >= 31) ConnectivityManager.NetworkCallback.FLAG_INCLUDE_LOCATION_INFO else 0
        val epoch = ++callbackEpoch
        val callback = if (Build.VERSION.SDK_INT >= 31) wifiCallbackWithFlags(flags, epoch) else wifiCallback(epoch)
        try {
            manager.registerNetworkCallback(NetworkRequest.Builder().addTransportType(NetworkCapabilities.TRANSPORT_WIFI).build(), callback)
            networkCallback = callback
        } catch (_: SecurityException) { networkCallback = null }
          catch (_: RuntimeException) { networkCallback = null }
    }

    private fun unregisterWifiCallback() {
        callbackEpoch++
        val callback = networkCallback ?: return
        networkCallback = null
        try { getSystemService(ConnectivityManager::class.java)?.unregisterNetworkCallback(callback) }
        catch (_: IllegalArgumentException) { }
        callbackWifi.clear()
    }

    private fun onWifiCapabilities(network: Network, capabilities: NetworkCapabilities, epoch: Int) {
        val info = capabilities.transportInfo as? WifiInfo
        runOnUiThread {
            if (visible && networkCallback != null && callbackEpoch == epoch) {
                if (info == null) callbackWifi.remove(network) else callbackWifi[network] = info
                scheduleConnectedRefresh()
            }
        }
    }

    private fun onWifiLost(network: Network, epoch: Int) {
        runOnUiThread { if (visible && networkCallback != null && callbackEpoch == epoch) { callbackWifi.remove(network); scheduleConnectedRefresh() } }
    }

    private fun scheduleConnectedRefresh() {
        if (refreshGate.request()) mainHandler.postDelayed(redrawConnected, 300)
    }

    private fun cancelScheduledRefresh() {
        refreshGate.cancel()
        mainHandler.removeCallbacks(redrawConnected)
    }

    private fun wifiCallback(epoch: Int) = object : ConnectivityManager.NetworkCallback() {
        override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) = onWifiCapabilities(network, capabilities, epoch)
        override fun onLost(network: Network) = onWifiLost(network, epoch)
    }

    private fun wifiCallbackWithFlags(flags: Int, epoch: Int) = object : ConnectivityManager.NetworkCallback(flags) {
        override fun onCapabilitiesChanged(network: Network, capabilities: NetworkCapabilities) = onWifiCapabilities(network, capabilities, epoch)
        override fun onLost(network: Network) = onWifiLost(network, epoch)
    }

    @Suppress("DEPRECATION")
    private fun refresh() {
        cancelScheduledRefresh()
        results.removeAllViews()
        val wifi = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        if (wifi == null) { label(card(results, "WI-FI"), "Wi-Fi is not available on this device."); return }
        val time = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.MEDIUM).format(Date())
        label(results, "Cached list read at $time · Wi-Fi ${if (wifi.isWifiEnabled) "enabled" else "off"}", 12f, "#9eb4c4")
        lastPermission = checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        lastLocationEnabled = getSystemService(LocationManager::class.java)?.isLocationEnabled == true
        lastWifiEnabled = wifi.isWifiEnabled
        if (!lastPermission) {
            label(card(results, "PERMISSION NEEDED"), "Precise location permission is needed for Wi-Fi details and nearby cached scans. Grant permission above; no scan will be started.")
            return
        }
        if (!lastLocationEnabled) {
            label(card(results, "LOCATION SERVICES OFF"), "Wi-Fi identities and nearby cached results may be unavailable.")
        }
        connectedHolder = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; results.addView(this) }
        renderConnected(wifi)
        val nearby = card(results, "NEARBY NETWORKS")
        label(nearby, "Cached observations · not a live scan or coverage survey", 12f, "#9eb4c4")
        val scans = try { wifi.scanResults } catch (_: SecurityException) { null } catch (_: IllegalStateException) { null }
        if (scans == null) {
            label(nearby, "Android did not expose cached scans. Check Wi-Fi permissions and location services.")
        } else if (scans.isEmpty()) {
            label(nearby, "No cached scan entries were exposed. This does not prove that no networks are present.")
        } else {
            val now = SystemClock.elapsedRealtime()
            label(nearby, "${scans.size} cached entries · showing up to 80 · strongest first", 12f)
            label(nearby, "Each bar is one reported network, not a history graph. Ages use Android monotonic timestamps.", 12f, "#9eb4c4")
            for (scan in scans.sortedByDescending { it.level }.take(80)) {
                val name = WifiSnapshotFormat.ssid(scan.SSID) ?: "SSID not exposed / hidden"
                val bssid = WifiSnapshotFormat.bssid(scan.BSSID) ?: "BSSID not exposed / redacted"
                val frequency = scan.frequency.takeIf { it > 0 }
                val entry = card(results, "CACHED WI-FI")
                label(entry, name, 17f, "#eef7fc", true)
                label(entry, "BSSID · $bssid", 12f)
                signalMeter(entry, scan.level)
                label(entry, WifiDisplay.channelText(frequency), 12f)
                label(entry, WifiDisplay.ageText(WifiSnapshotFormat.ageSeconds(now, scan.timestamp)), 12f, "#9eb4c4")
            }
        }
    }

    private fun refreshConnected() {
        val wifi = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        val permission = checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED
        val locationEnabled = getSystemService(LocationManager::class.java)?.isLocationEnabled == true
        if (wifi == null || permission != lastPermission || locationEnabled != lastLocationEnabled || wifi.isWifiEnabled != lastWifiEnabled) {
            refresh()
            return
        }
        if (permission && ::connectedHolder.isInitialized) renderConnected(wifi)
    }

    @Suppress("DEPRECATION")
    private fun renderConnected(wifi: WifiManager) {
        connectedHolder.removeAllViews()
        val connectivity = getSystemService(ConnectivityManager::class.java)
        val networks = try { connectivity?.allNetworks?.toList().orEmpty() } catch (_: SecurityException) { emptyList() }
        val active = try { connectivity?.activeNetwork } catch (_: SecurityException) { null }
        val wifiNetworks = networks.filter { network ->
            try { connectivity?.getNetworkCapabilities(network)?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true }
            catch (_: SecurityException) { false }
        }
        val wifiNetwork = wifiNetworks.firstOrNull { it == active } ?: wifiNetworks.firstOrNull()
        val info = try {
            val bound = (wifiNetwork?.let { callbackWifi[it] }) ?:
                (wifiNetwork?.let { connectivity?.getNetworkCapabilities(it)?.transportInfo } as? WifiInfo)
            WifiSnapshotFormat.association(wifiNetwork != null, bound) { wifi.connectionInfo }
        } catch (_: SecurityException) { null }
        val connected = card(connectedHolder, "CONNECTED WI-FI")
        val time = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.MEDIUM).format(Date())
        label(connected, "Read at $time · system sample age not exposed", 12f, "#9eb4c4")
        if (wifiNetwork == null && (info == null || info.networkId == -1)) {
            label(connected, "No associated Wi-Fi network is exposed by Android.")
        } else {
            if (wifiNetwork != null) label(connected, if (wifiNetwork == active) "Default network" else "Wi-Fi present · not the default network", 12f)
            val frequency = info?.frequency?.takeIf { it > 0 }
            label(connected, WifiSnapshotFormat.ssid(info?.ssid) ?: "Network name not exposed / redacted", 19f, "#eef7fc", true)
            label(connected, "BSSID · ${WifiSnapshotFormat.bssid(info?.bssid) ?: "Not exposed / redacted"}", 12f)
            signalMeter(connected, info?.rssi)
            label(connected, WifiDisplay.channelText(frequency))
            label(connected, "Link rate · ${info?.linkSpeed?.takeIf { it > 0 }?.let { "$it Mbps" } ?: "Not exposed"} · negotiated, not measured throughput", 12f)
        }
    }
}
