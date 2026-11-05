package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import android.os.Build
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.text.DateFormat
import java.util.Date

/** Local, on-demand Android network inventory. It performs no traffic or device enumeration. */
class NetworkInventoryWorkspace(context: Context) : LinearLayout(context) {
    private val output = LinearLayout(context)
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun label(parent: LinearLayout, value: String, size: Float = 13f, bold: Boolean = false): TextView = TextView(context).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(if (bold) "#e8f5fa" else "#b8cbd9"))
        if (bold) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(4), 0, dp(5)); parent.addView(this)
    }

    init {
        orientation = VERTICAL
        setPadding(dp(14), dp(12), dp(14), dp(14))
        background = GradientDrawable().apply {
            setColor(Color.parseColor("#111d2a")); setStroke(dp(1), Color.parseColor("#2a4051")); cornerRadius = dp(8).toFloat()
        }
        label(this, "NETWORK INTERFACES", 16f, true)
        label(this, "Read Android's visible network state, including USB Ethernet when Android recognizes it. No scan or network request is made. IP and DNS details stay on this phone.")
        addView(Button(context).apply {
            text = "Refresh network interfaces"; isAllCaps = false; minHeight = dp(48)
            backgroundTintList = ColorStateList.valueOf(Color.parseColor("#243b50")); setTextColor(Color.WHITE)
            setOnClickListener { refresh() }
        })
        output.orientation = VERTICAL
        addView(output)
        label(output, "Tap refresh to inspect the networks currently visible to Android.")
    }

    @Suppress("DEPRECATION")
    private fun refresh() {
        output.removeAllViews()
        val manager = context.getSystemService(ConnectivityManager::class.java)
        if (manager == null) { label(output, "Android connectivity service is unavailable."); return }
        try {
            val active = manager.activeNetwork
            val networks = manager.allNetworks.toList()
            label(output, "Read at ${DateFormat.getTimeInstance(DateFormat.MEDIUM).format(Date())} · ${networks.size} visible network(s)", 12f)
            if (networks.isEmpty()) {
                label(output, "No networks are exposed to this app. An attached adapter may need Android driver or network support.")
                return
            }
            for (network in networks.take(24)) {
                // Each property is queried for the same Android network object. The network may
                // disappear during this snapshot; unavailable properties remain explicitly blank.
                val caps = manager.getNetworkCapabilities(network)
                val link = manager.getLinkProperties(network)
                val transports = buildList {
                    if (caps?.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) == true) add("Wi-Fi")
                    if (caps?.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) == true) add("Cellular")
                    if (caps?.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET) == true) add("Ethernet")
                    if (caps?.hasTransport(NetworkCapabilities.TRANSPORT_VPN) == true) add("VPN")
                    if (caps?.hasTransport(NetworkCapabilities.TRANSPORT_BLUETOOTH) == true) add("Bluetooth")
                    if (Build.VERSION.SDK_INT >= 31 && caps?.hasTransport(NetworkCapabilities.TRANSPORT_USB) == true) add("USB")
                }
                val privateDns = link?.let {
                    when {
                        !it.isPrivateDnsActive -> "not active"
                        !it.privateDnsServerName.isNullOrBlank() -> "active · ${it.privateDnsServerName}"
                        else -> "active · opportunistic"
                    }
                }
                val snapshot = NetworkInventoryFormat.Snapshot(
                    active = active?.let { it == network }, transports = transports,
                    internet = caps?.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET),
                    validated = caps?.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED),
                    captivePortal = caps?.hasCapability(NetworkCapabilities.NET_CAPABILITY_CAPTIVE_PORTAL),
                    metered = caps?.let { !it.hasCapability(NetworkCapabilities.NET_CAPABILITY_NOT_METERED) },
                    interfaceName = link?.interfaceName,
                    addresses = link?.linkAddresses?.take(24)?.map { "${it.address.hostAddress}/${it.prefixLength}" }.orEmpty(),
                    dns = link?.dnsServers?.take(12)?.mapNotNull { it.hostAddress }.orEmpty(),
                    routes = link?.routes?.take(24)?.map { route ->
                        val gateway = route.gateway?.hostAddress
                        "${route.destination}" + if (gateway == null || route.gateway?.isAnyLocalAddress == true) " · on-link" else " via $gateway"
                    }.orEmpty(),
                    mtu = link?.mtu, privateDns = privateDns
                )
                label(output, NetworkInventoryFormat.describe(snapshot), 13f).apply {
                    setPadding(dp(10), dp(10), dp(10), dp(10))
                    background = GradientDrawable().apply { setColor(Color.parseColor("#172a3b")); cornerRadius = dp(8).toFloat() }
                    (layoutParams as? LayoutParams)?.topMargin = dp(8)
                    setTextIsSelectable(true)
                }
            }
            if (networks.size > 24) label(output, "Additional networks omitted from this display.", 12f)
            label(output, "Snapshot only. Android may omit networks or fields; a VPN can hide the underlying path. Validation and MTU are system-reported, not measured throughput or a verified end-to-end path.", 12f)
        } catch (_: SecurityException) {
            output.removeAllViews(); label(output, "Android did not permit network-state inspection.")
        } catch (_: RuntimeException) {
            output.removeAllViews(); label(output, "Network state changed while reading it. Refresh to try again.")
        }
    }
}
