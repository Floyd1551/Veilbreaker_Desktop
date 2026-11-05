package com.veilbreaker.companion

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.location.LocationManager
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.telephony.CellInfo
import android.telephony.SubscriptionManager
import android.telephony.TelephonyManager
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject
import java.text.DateFormat
import java.util.Date

/** Explicit, foreground-only display of Android cell callbacks; never saves evidence. */
class LiveCellWorkspace(
    context: Context,
    private val selectedSubscriptionId: () -> Int?,
    private val canRun: () -> Boolean,
    private val channelPlan: () -> JSONObject
) : LinearLayout(context) {
    private val handler = Handler(Looper.getMainLooper())
    private val status = TextView(context)
    private val details = TextView(context)
    private val button = Button(context)
    private var active = false
    private var collectionBlocked = false
    private var generation = 0L
    private var requestId = 0L
    private var subscriptionId: Int? = null
    private var shownSubscriptionId: Int? = null
    private var nextRequest: Runnable? = null
    private var timeout: Runnable? = null
    private var endSession: Runnable? = null
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()

    init {
        orientation = VERTICAL
        addView(TextView(context).apply {
            text = "LIVE CELLULAR MONITOR"; textSize = 16f; setTypeface(null, Typeface.BOLD)
            setTextColor(Color.parseColor("#63d6ee")); setPadding(0, dp(12), 0, dp(6))
        })
        addView(TextView(context).apply {
            text = "Explicit foreground view only. Android may return cached or incomplete readings; requests are at least 10 seconds apart and stop after five minutes. Nothing here is saved as evidence."
            textSize = 13f; setTextColor(Color.parseColor("#b8cbd9"))
        })
        button.apply { text = "Start live cellular"; isAllCaps = false; minHeight = dp(48); setOnClickListener { if (active) stop() else start() } }
        addView(button)
        status.apply { text = "Live monitor off. Choose a SIM and start when ready."; textSize = 13f; setTextColor(Color.parseColor("#b8cbd9")); setPadding(0, dp(5), 0, dp(5)) }
        details.apply { textSize = 13f; setTextColor(Color.parseColor("#e8f5fa")); setTextIsSelectable(true); setPadding(0, dp(5), 0, dp(10)) }
        addView(status); addView(details)
    }

    fun selectionChanged() {
        val selected = selectedSubscriptionId()
        if (active && selected != subscriptionId) stop("SIM changed. Start the live monitor again for the selected SIM.")
        if (shownSubscriptionId != selected) { details.text = ""; shownSubscriptionId = null }
    }
    fun setCollectionBlocked(blocked: Boolean) {
        collectionBlocked = blocked
        if (blocked && active) stop("Live monitor stopped while another capture or Desktop session is active.")
        if (blocked) { details.text = ""; shownSubscriptionId = null }
        button.isEnabled = !blocked
    }
    fun stop(message: String = "Live monitor stopped. No readings were saved.") {
        if (!active) return
        active = false; generation++; requestId++; subscriptionId = null
        nextRequest?.let(handler::removeCallbacks); timeout?.let(handler::removeCallbacks); endSession?.let(handler::removeCallbacks)
        nextRequest = null; timeout = null; endSession = null
        button.text = "Start live cellular"; status.text = message
    }

    private fun ready(id: Int): Boolean {
        if (collectionBlocked || !canRun() || !isShown) return false
        if (context.checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED ||
            context.checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) return false
        val locations = context.getSystemService(LocationManager::class.java)
        if (locations?.isLocationEnabled != true) return false
        return try { context.getSystemService(SubscriptionManager::class.java)?.activeSubscriptionInfoList?.any { it.subscriptionId == id } == true }
            catch (_: RuntimeException) { false }
    }

    private fun start() {
        val id = selectedSubscriptionId()
        if (id == null) { status.text = "Choose a SIM in Phone inputs before starting."; return }
        if (!ready(id)) { status.text = "Choose an active SIM, grant phone and precise location permissions, enable location services, and stop other collection first."; return }
        active = true; subscriptionId = id; val token = ++generation
        button.text = "Stop live cellular"; status.text = "Requesting a cell update…"; details.text = ""; shownSubscriptionId = null
        endSession = Runnable { if (active && token == generation) stop("Five-minute limit reached. No live readings were saved.") }.also { handler.postDelayed(it, MAX_DURATION_MS) }
        request(token, id)
    }

    @SuppressLint("MissingPermission")
    private fun request(token: Long, id: Int) {
        nextRequest = null
        if (!active || token != generation) return
        if (selectedSubscriptionId() != id || !ready(id)) { stop("Live monitor stopped because the SIM, permissions, screen, or collection state changed."); return }
        val started = SystemClock.elapsedRealtime()
        val request = ++requestId
        fun complete(cells: List<CellInfo>?, error: String?) {
            if (!active || token != generation || request != requestId) return
            requestId++
            timeout?.let(handler::removeCallbacks); timeout = null
            if (selectedSubscriptionId() != id || !ready(id)) { stop("Live monitor stopped because the SIM, permissions, screen, or collection state changed."); return }
            val now = SystemClock.elapsedRealtime()
            if (error != null) {
                status.text = "$error · retrying while this screen remains open."
                details.text = ""; shownSubscriptionId = null
            } else {
                val values = cells.orEmpty().take(MAX_CELLS).mapNotNull { runCatching { CellularSnapshot.cell(it, now) }.getOrNull() }
                val rendered = runCatching { LiveCellSummary.render(values, channelPlan()) }.getOrElse { "Cell details are unavailable for this response." }
                val omitted = (cells.orEmpty().size - values.size).coerceAtLeast(0)
                status.text = "Response received ${DateFormat.getTimeInstance(DateFormat.MEDIUM).format(Date())}. Modem sample age is shown at receipt; a new response may be cached."
                details.text = rendered + if (omitted > 0) "\n\n$omitted reports omitted or unreadable." else ""
                shownSubscriptionId = id
            }
            val delay = (MIN_INTERVAL_MS - (SystemClock.elapsedRealtime() - started)).coerceAtLeast(0)
            nextRequest = Runnable { request(token, id) }.also { handler.postDelayed(it, delay) }
        }
        timeout = Runnable { complete(null, "Cell update timed out") }.also { handler.postDelayed(it, TIMEOUT_MS) }
        try {
            val telephony = context.getSystemService(TelephonyManager::class.java).createForSubscriptionId(id)
            telephony.requestCellInfoUpdate(context.mainExecutor, object : TelephonyManager.CellInfoCallback() {
                override fun onCellInfo(cellInfo: MutableList<CellInfo>) { complete(cellInfo, null) }
                override fun onError(errorCode: Int, detail: Throwable?) { complete(null, "Cell update unavailable") }
            })
        } catch (_: RuntimeException) { complete(null, "Cell update unavailable") }
    }

    override fun onDetachedFromWindow() { stop(); super.onDetachedFromWindow() }
    override fun onWindowVisibilityChanged(visibility: Int) { super.onWindowVisibilityChanged(visibility); if (visibility != View.VISIBLE) stop() }
    override fun onVisibilityChanged(changedView: View, visibility: Int) { super.onVisibilityChanged(changedView, visibility); if (visibility != View.VISIBLE) stop() }

    private companion object { const val MIN_INTERVAL_MS = 10_000L; const val TIMEOUT_MS = 12_000L; const val MAX_DURATION_MS = 300_000L; const val MAX_CELLS = 256 }
}
