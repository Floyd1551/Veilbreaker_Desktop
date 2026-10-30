package com.veilbreaker.companion

import android.Manifest
import android.app.Activity
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.location.LocationManager
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.net.NetworkRequest
import android.net.wifi.WifiInfo
import android.net.wifi.WifiManager
import android.os.Build
import android.os.Bundle
import android.os.SystemClock
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.text.DateFormat
import java.util.Date

/** Foreground, read-only view of platform Wi-Fi observations. No scan is initiated. */
class WifiSnapshotActivity : Activity() {
    private lateinit var results: TextView
    private var visible = false
    private var networkCallback: ConnectivityManager.NetworkCallback? = null
    private var callbackEpoch = 0
    private val callbackWifi = mutableMapOf<Network, WifiInfo>()
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        window.statusBarColor = Color.parseColor("#0d1520")
        window.navigationBarColor = Color.parseColor("#0d1520")
        val scroll = ScrollView(this).apply { setBackgroundColor(Color.parseColor("#0d1520")); isFillViewport = true }
        val content = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(dp(20), dp(24), dp(20), dp(24)) }
        scroll.addView(content); setContentView(scroll)
        fun text(value: String, size: Float) = TextView(this).apply {
            text = value; textSize = size; setTextColor(Color.parseColor("#d4e2ed")); setPadding(0, dp(8), 0, dp(8)); content.addView(this)
        }
        fun button(value: String, action: () -> Unit) = Button(this).apply {
            this.text = value; isAllCaps = false; minHeight = dp(48); setOnClickListener { action() }; content.addView(this)
        }
        text("WI-FI ENVIRONMENT", 22f).apply { setTypeface(null, Typeface.BOLD); setTextColor(Color.parseColor("#63dec8")) }
        text("Read-only, foreground view. Nearby entries are cached Android results, not a new scan. Network names and addresses are not saved or exported by this view.", 14f)
        button("Grant Wi-Fi permissions") { requestWifiPermissions() }
        button("Refresh cached results") { refresh() }
        results = text("Reading Wi-Fi…", 15f)
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
        registerWifiCallback()
    }

    override fun onStop() {
        visible = false
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
                refresh()
            }
        }
    }

    private fun onWifiLost(network: Network, epoch: Int) {
        runOnUiThread { if (visible && networkCallback != null && callbackEpoch == epoch) { callbackWifi.remove(network); refresh() } }
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
        val wifi = applicationContext.getSystemService(Context.WIFI_SERVICE) as? WifiManager
        if (wifi == null) { results.text = "Wi-Fi is not available on this device."; return }
        val time = DateFormat.getDateTimeInstance(DateFormat.SHORT, DateFormat.MEDIUM).format(Date())
        val lines = mutableListOf("Read at $time", "Wi-Fi: ${if (wifi.isWifiEnabled) "enabled" else "off"}")
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            lines.add("Precise location permission is needed to read Android Wi-Fi details and nearby cached scans. Grant permission above; no scan will be started.")
            results.text = lines.joinToString("\n"); return
        }
        val location = getSystemService(LocationManager::class.java)
        if (location == null || !location.isLocationEnabled) {
            lines.add("Android location services are off; Wi-Fi identities and nearby cached results may be unavailable.")
        }
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
        lines.add("")
        lines.add("CONNECTED WI-FI · current system values; sample age not exposed")
        if (wifiNetwork == null && (info == null || info.networkId == -1)) {
            lines.add("No associated Wi-Fi network is exposed by Android.")
        } else {
            if (wifiNetwork != null) lines.add(if (wifiNetwork == active) "Wi-Fi is the default network." else "Wi-Fi is present; it is not the default network.")
            val frequency = info?.frequency?.takeIf { it > 0 }
            val channel = frequency?.let { WifiSnapshotFormat.channel(it) }
            lines.add("Network: ${WifiSnapshotFormat.ssid(info?.ssid) ?: "Not exposed / redacted"}")
            lines.add("BSSID: ${WifiSnapshotFormat.bssid(info?.bssid) ?: "Not exposed / redacted"}")
            lines.add("Signal: ${info?.rssi?.takeIf { it > -127 && it <= 0 }?.let { "$it dBm" } ?: "Not exposed"}")
            lines.add("Frequency: ${frequency?.let { "$it MHz" } ?: "Not exposed"} · channel: ${channel?.toString() ?: "Unknown"} (derived)")
            lines.add("Link rate: ${info?.linkSpeed?.takeIf { it > 0 }?.let { "$it Mbps" } ?: "Not exposed"} · negotiated, not measured throughput")
        }
        lines.add("")
        lines.add("NEARBY WI-FI · cached scan entries, not a coverage survey")
        val scans = try { wifi.scanResults } catch (_: SecurityException) { null } catch (_: IllegalStateException) { null }
        if (scans == null) {
            lines.add("Android did not expose cached scans. Check Wi-Fi permissions and location services.")
        } else if (scans.isEmpty()) {
            lines.add("No cached scan entries were exposed. This does not prove that no networks are present.")
        } else {
            val now = SystemClock.elapsedRealtime()
            lines.add("${scans.size} cached entries · showing up to 80; ages are estimated from Android monotonic timestamps.")
            for (scan in scans.sortedByDescending { it.level }.take(80)) {
                val name = WifiSnapshotFormat.ssid(scan.SSID) ?: "SSID not exposed / hidden"
                val bssid = WifiSnapshotFormat.bssid(scan.BSSID) ?: "BSSID not exposed / redacted"
                val frequency = scan.frequency.takeIf { it > 0 }
                val channel = frequency?.let { WifiSnapshotFormat.channel(it) }
                val age = WifiSnapshotFormat.ageSeconds(now, scan.timestamp)?.let { "$it s old" } ?: "age unavailable"
                val signal = scan.level.takeIf { it > -127 && it <= 0 }?.let { "$it dBm" } ?: "signal unavailable"
                lines.add("\n$name · $bssid\n$signal · ${frequency?.let { "$it MHz" } ?: "frequency unavailable"} · channel ${channel ?: "unknown"} (derived) · $age")
            }
        }
        results.text = lines.joinToString("\n")
    }
}
