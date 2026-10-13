package com.veilbreaker.companion

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.location.LocationManager
import android.os.*
import android.telephony.*
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.time.Instant

/** Snapshot-only first increment. No service, network listener or background collection. */
class MainActivity : Activity() {
    private val handler = Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var preview: TextView
    private lateinit var subscriptions: Spinner
    private lateinit var captureButton: Button
    private lateinit var exportButton: Button
    private var choices: List<SubscriptionInfo> = emptyList()
    private var generation = 0
    private var pending = false
    private var usb: UsbSession? = null
    private var endpoint: LoopbackEndpoint? = null
    private lateinit var usbStatus: TextView
    private var capture: JSONObject? = null
    private var exportText: String? = null
    private val permissions = arrayOf(Manifest.permission.READ_PHONE_STATE, Manifest.permission.ACCESS_COARSE_LOCATION, Manifest.permission.ACCESS_FINE_LOCATION)

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val scroll = ScrollView(this)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(24,48,24,32) }
        scroll.addView(layout); setContentView(scroll)
        fun text(value: String) = TextView(this).apply { text = value; setPadding(0,12,0,12); layout.addView(this) }
        fun button(value: String, action: () -> Unit) = Button(this).apply { text = value; setOnClickListener { action() }; layout.addView(this) }
        text("Veilbreaker Companion â€¢ Development snapshot").textSize = 23f
        text("Read the cellular measurements Android exposes. Phone and precise-location permission allow cell information access; this version does not collect GPS coordinates. No raw modem feed or background capture.")
        button("Grant permissions / refresh SIMs") {
            if (allowed()) refresh() else requestPermissions(permissions, 1)
        }
        subscriptions = Spinner(this); layout.addView(subscriptions)
        captureButton = button("Capture selected SIM snapshot") { takeSnapshot() }
        button("Stop pending request / USB session") { stopUsb(); cancelPending() }
        button("Connect to Veilbreaker") { armUsb() }
        usbStatus = text("USB collection is disconnected. Select a SIM and tap Connect to Veilbreaker. Keep this app visible.")
        exportButton = button("Export capture JSON") {
            capture?.let {
                exportText = it.toString(2)
                startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE); type = "application/json"
                    putExtra(Intent.EXTRA_TITLE, "veilbreaker-${it.getString("capture_id")}.json")
                }, 2)
            }
        }
        status = text("Grant permissions, select a SIM, then capture. Android may return cached or incomplete information.")
        preview = text("")
        capture = try { JSONObject(filesDir.resolve("last-capture.json").readText()) } catch (_: Exception) { null }
        showCapture()
        refresh()
    }

    private fun allowed() = checkSelfPermission(Manifest.permission.READ_PHONE_STATE) == PackageManager.PERMISSION_GRANTED &&
        checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED

    private fun refresh() {
        if (usb != null) return
        choices = if (allowed()) try { getSystemService(SubscriptionManager::class.java).activeSubscriptionInfoList ?: emptyList() } catch (_: SecurityException) { emptyList() } else emptyList()
        subscriptions.adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item,
            listOf("Choose a SIMâ€¦") + choices.map { "SIM slot ${it.simSlotIndex + 1} Â· ${it.displayName}" })
        captureButton.isEnabled = usb == null && allowed() && choices.isNotEmpty() && !pending
        if (choices.isEmpty()) status.text = "No available subscription, or permissions are missing. No capture started."
    }

    override fun onRequestPermissionsResult(code: Int, p: Array<out String>, results: IntArray) {
        super.onRequestPermissionsResult(code,p,results)
        if (code == 1) refresh()
    }

    private fun takeSnapshot() {
        if (pending || !allowed()) { if (!allowed()) usb?.finish("partial"); status.text = "Grant phone and precise-location permissions first."; return }
        val selected = choices.getOrNull(subscriptions.selectedItemPosition - 1)
        if (selected == null) { status.text = "Choose a SIM explicitly."; return }
        if (!getSystemService(LocationManager::class.java).isLocationEnabled) {
            status.text = "Enable Android location services to allow cell information access. GPS coordinates will not be recorded."; return
        }
        val started = Instant.now().toString()
        val token = ++generation
        pending = true; captureButton.isEnabled = false; exportButton.isEnabled = false; subscriptions.isEnabled = false
        status.text = "Requesting public cell informationâ€¦"
        fun finish(cells: List<CellInfo>?, error: String?) {
            if (generation != token || !pending) return
            pending = false; subscriptions.isEnabled = usb == null
            val elapsed = SystemClock.elapsedRealtime()
            try {
                val stillPresent = getSystemService(SubscriptionManager::class.java).activeSubscriptionInfoList?.any { it.subscriptionId == selected.subscriptionId } == true
                val notes = mutableListOf("Single public-API snapshot. LTE/NR fields supported; other radio types are reference records only. No continuous sampling.")
                if (error != null) notes.add(error)
                if (!stillPresent) notes.add("Selected subscription disappeared; results discarded.")
                val source = if (stillPresent) cells.orEmpty() else emptyList()
                if (source.isEmpty()) notes.add("No cell observations returned. Android may rate-limit updates.")
                if (source.size > 256) notes.add("Cell list limited to first 256 entries.")
                val outcome = if (error != null || source.isEmpty() || source.size > 256) "partial" else "complete"
                val snapshot = CaptureSerializer.envelope(Build.MANUFACTURER, Build.MODEL, Build.VERSION.RELEASE,
                    Build.VERSION.SDK_INT, "0.3.0-dev", source.take(256).map { CellularSnapshot.cell(it,elapsed) }, elapsed, outcome, notes, started)
                val selectedManager = getSystemService(TelephonyManager::class.java).createForSubscriptionId(selected.subscriptionId)
                snapshot.getJSONArray("subscriptions").getJSONObject(0)
                    .put("network_operator", selectedManager.networkOperatorName)
                    .put("sim_carrier", selected.carrierName?.toString() ?: "")
                    .put("slot_index", selected.simSlotIndex)
                snapshot.getJSONObject("collection").put("permissions", JSONObject().put("phone_state", "granted").put("fine_location", "granted"))
                if (usb != null) {
                    usb!!.accept(snapshot)
                    if (error != null || !stillPresent || !allowed()) usb!!.finish("partial")
                } else {
                    capture = snapshot
                    filesDir.resolve("last-capture.json").writeText(snapshot.toString())
                }
                status.text = "Snapshot saved locally. Review and export it to Desktop. Completion does not mean every modem field was available."
            } catch (e: Exception) {
                usb?.finish("partial")
                status.text = "Snapshot failed: ${e.message}. Any previous saved capture remains available."
            }
            showCapture(); captureButton.isEnabled = usb == null && allowed() && choices.isNotEmpty()
        }
        handler.postDelayed({ finish(null,"Cell-info request timed out after 15 seconds.") }, 15000)
        try {
            getSystemService(TelephonyManager::class.java).createForSubscriptionId(selected.subscriptionId)
                .requestCellInfoUpdate(mainExecutor, object : TelephonyManager.CellInfoCallback() {
                    override fun onCellInfo(cellInfo: MutableList<CellInfo>) { finish(cellInfo,null) }
                    override fun onError(errorCode: Int, detail: Throwable?) { finish(null,"Cell-info error $errorCode: ${detail?.message ?: "unavailable"}") }
                })
        } catch (e: Exception) { finish(null,e.message ?: "Cell information unavailable") }
    }

    private fun showCapture() {
        preview.text = capture?.toString(2)?.take(20000) ?: "No saved capture."
        exportButton.isEnabled = capture != null && !pending && usb == null
    }
    private fun cancelPending() {
        if (pending) status.text = "Pending request stopped. Previously saved capture is unchanged."
        generation++; pending = false; handler.removeCallbacksAndMessages(null)
        subscriptions.isEnabled = true; captureButton.isEnabled = usb == null && allowed() && choices.isNotEmpty(); showCapture()
    }
    private fun armUsb() {
        if (pending || usb != null || !allowed() || choices.getOrNull(subscriptions.selectedItemPosition - 1) == null) {
            status.text = "Grant permissions, choose a SIM and stop any pending request before arming."; return
        }
        if (!getSystemService(LocationManager::class.java).isLocationEnabled) {
            status.text = "Enable Android location services before arming."; return
        }
        val session = UsbSession({ SystemClock.elapsedRealtime() }, { takeSnapshot() }, { value ->
            capture = value
            filesDir.resolve("last-capture.json").writeText(value.toString())
            showCapture()
        })
        usb = session
        val pairing = UsbPairing({ SystemClock.elapsedRealtime() }, session.token)
        try {
            endpoint = LoopbackEndpoint { name, token, body ->
                val latch = java.util.concurrent.CountDownLatch(1)
                var response: JSONObject? = null
                handler.post {
                    try {
                        if (usb === session) {
                            if (name == "pair" || name == "pair_status") {
                                val pairId = body.getString("pair_id")
                                response = JSONObject().put("protocol", 1).put("request_id", body.getString("request_id"))
                                    .put("session_id", session.id).put("status", "armed")
                                if (name == "pair") {
                                    val code = body.getString("code")
                                    pairing.begin(pairId, code)
                                    android.app.AlertDialog.Builder(this)
                                        .setTitle("Connect to Veilbreaker?")
                                        .setMessage("Confirm this code matches Desktop: $code\nOnly approve the connection you just requested.")
                                        .setPositiveButton("Codes match - connect") { _, _ ->
                                            runCatching { if (usb === session) pairing.approve(pairId) }
                                        }
                                        .setNegativeButton("Reject") { _, _ -> pairing.deny() }
                                        .setOnCancelListener { pairing.deny() }.show()
                                } else {
                                    val credential = pairing.poll(pairId)
                                    response!!.put("paired", credential != null)
                                    if (credential != null) response!!.put("token", credential)
                                }
                            } else response = session.command(name, token, body)
                        }
                    } catch (_: Exception) { } finally { latch.countDown() }
                }
                require(latch.await(2, java.util.concurrent.TimeUnit.SECONDS))
                response ?: throw IllegalArgumentException("Session unavailable")
            }
            usbStatus.text = "Ready for Desktop. Select Live Android USB, then Connect. Confirm the matching six-digit code here. Keep this app visible."
            usbStatus.setTextIsSelectable(true)
            subscriptions.isEnabled = false; captureButton.isEnabled = false; exportButton.isEnabled = false
            window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            fun tick() {
                if (usb !== session) return
                session.expire()
                handler.postDelayed({ tick() }, 1000)
            }
            tick()
        } catch (_: Exception) {
            usb = null; status.text = "Cannot open USB endpoint. Stop another companion instance and try again."
        }
    }

    private fun stopUsb() {
        endpoint?.close(); endpoint = null
        usb?.finish("cancelled"); usb = null
        usbStatus.text = "USB session stopped. Tap Connect to Veilbreaker for a new connection."
        window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }
    override fun onStop() { stopUsb(); cancelPending(); super.onStop() }

    @Deprecated("Platform activity result used to keep the initial companion dependency-light")
    override fun onActivityResult(request: Int, result: Int, data: Intent?) {
        super.onActivityResult(request,result,data)
        if (request == 2 && result == RESULT_OK && data?.data != null) {
            try {
                val bytes = exportText ?: capture?.toString(2) ?: error("No capture to export")
                contentResolver.openOutputStream(data.data!!, "wt")?.use { it.write(bytes.toByteArray(Charsets.UTF_8)) } ?: error("Cannot open export destination")
                status.text = "JSON exported. Copy it over USB and choose Import Android capture in Desktop."
            } catch (e: Exception) { status.text = "Export failed: ${e.message}" }
        }
        exportText = null
    }
}
