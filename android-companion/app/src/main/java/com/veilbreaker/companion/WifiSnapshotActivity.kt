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
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.Spinner
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
    private var filterQuery = ""
    private var filterBand = WifiObservationFilter.Band.ALL
    private var filterOrder = WifiObservationFilter.Order.SIGNAL
    private var pendingListRender: Runnable? = null
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
        if (state != null) {
            filterQuery = state.getString("wifi_filter_query", "").take(128)
            filterBand = WifiObservationFilter.Band.entries.getOrElse(state.getInt("wifi_filter_band", 0)) { WifiObservationFilter.Band.ALL }
            filterOrder = WifiObservationFilter.Order.entries.getOrElse(state.getInt("wifi_filter_order", 0)) { WifiObservationFilter.Order.SIGNAL }
        }
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

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putString("wifi_filter_query", filterQuery)
        outState.putInt("wifi_filter_band", filterBand.ordinal)
        outState.putInt("wifi_filter_order", filterOrder.ordinal)
        super.onSaveInstanceState(outState)
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
        cancelListRender()
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

    private fun cancelListRender() {
        pendingListRender?.let(mainHandler::removeCallbacks)
        pendingListRender = null
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
        cancelListRender()
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
        } else {
            val now = SystemClock.elapsedRealtime()
            val strongest = scans.sortedByDescending { it.level }
            if (scans.isEmpty()) label(nearby, "No cached scan entries were exposed. This does not prove that no networks are present.")
            label(nearby, "${scans.size} cached entries · chart uses up to 500 strongest and is not affected by list filters. Filters examine up to 2,000 entries; list shows up to 80.", 12f)
            label(nearby, "Ages are calculated when the cached list is read, not when filtered. No new scan is started.", 12f, "#9eb4c4")
            val chart = strongest.take(500).map { scan ->
                WifiChannelPlotModel.Sample(scan.frequency, scan.level, WifiSnapshotFormat.ageSeconds(now, scan.timestamp))
            }
            results.addView(WifiChannelChartWorkspace(this, chart), LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(12) })
            val rows = scans.take(2000).map { scan ->
                WifiObservationFilter.Row(WifiSnapshotFormat.ssid(scan.SSID), WifiSnapshotFormat.bssid(scan.BSSID), scan.frequency, scan.level, WifiSnapshotFormat.ageSeconds(now, scan.timestamp))
            }
            showObservationFilters(rows, scans.size)
        }
    }

    private fun showObservationFilters(rows: List<WifiObservationFilter.Row>, total: Int) {
        val filter = card(results, "FIND CACHED NETWORKS")
        label(filter, "Filter this cached list by network name, BSSID, or band. Changing a filter does not refresh the observations.", 12f)
        val search = EditText(this).apply {
            hint = "Search SSID or BSSID"; contentDescription = "Search cached Wi-Fi by SSID or BSSID"
            setSingleLine(true); setTextColor(Color.WHITE); setHintTextColor(color("#a7bac9"))
            filters = arrayOf(android.text.InputFilter.LengthFilter(128)); setText(filterQuery)
        }
        filter.addView(search)
        val band = Spinner(this).apply {
            contentDescription = "Filter cached Wi-Fi by band"
            adapter = ArrayAdapter(this@WifiSnapshotActivity, android.R.layout.simple_spinner_dropdown_item, listOf("All bands", "2.4 GHz", "5 GHz", "6 GHz"))
            setSelection(filterBand.ordinal)
        }
        filter.addView(band)
        val order = Spinner(this).apply {
            contentDescription = "Sort cached Wi-Fi"
            adapter = ArrayAdapter(this@WifiSnapshotActivity, android.R.layout.simple_spinner_dropdown_item, listOf("Strongest signal first", "Frequency", "Newest cached sample first"))
            setSelection(filterOrder.ordinal)
        }
        filter.addView(order)
        val summary = label(filter, "", 12f)
        val list = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; results.addView(this) }
        fun renderList() {
            list.removeAllViews()
            val selected = WifiObservationFilter.select(rows, filterQuery, filterBand, filterOrder)
            summary.text = "${selected.size} matching cached entries${if (total > rows.size) " · ${total - rows.size} beyond filter limit" else ""}; showing up to 80."
            if (selected.isEmpty()) label(list, "No matching cached entries. This does not mean the network or band is absent.", 13f)
            for (row in selected.take(80)) {
                val entry = card(list, "CACHED WI-FI")
                label(entry, row.ssid ?: "SSID not exposed / hidden", 17f, "#eef7fc", true)
                label(entry, "BSSID · ${row.bssid ?: "Not exposed / redacted"}", 12f)
                signalMeter(entry, row.rssiDbm)
                label(entry, WifiDisplay.channelText(row.frequencyMhz.takeIf { it > 0 }), 12f)
                label(entry, row.ageSeconds?.let { "$it s old when cached list was read" } ?: "Age unavailable", 12f, "#9eb4c4")
            }
        }
        fun scheduleRender() {
            cancelListRender()
            if (!visible) return
            val render = Runnable { pendingListRender = null; if (visible && !isFinishing && !isDestroyed) renderList() }
            pendingListRender = render; mainHandler.postDelayed(render, 180)
        }
        search.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { filterQuery = s?.toString().orEmpty(); scheduleRender() }
            override fun afterTextChanged(s: Editable?) {}
        })
        band.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) { filterBand = WifiObservationFilter.Band.entries.getOrElse(position) { WifiObservationFilter.Band.ALL }; scheduleRender() }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
        order.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) { filterOrder = WifiObservationFilter.Order.entries.getOrElse(position) { WifiObservationFilter.Order.SIGNAL }; scheduleRender() }
            override fun onNothingSelected(parent: AdapterView<*>?) {}
        }
        renderList()
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
