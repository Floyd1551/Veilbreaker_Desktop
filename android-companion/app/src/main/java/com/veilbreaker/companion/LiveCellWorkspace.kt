package com.veilbreaker.companion

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
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
import java.time.Instant

/** Explicit, foreground-only display of Android cell callbacks; never saves evidence. */
class LiveCellWorkspace(
    context: Context,
    private val selectedSubscriptionId: () -> Int?,
    private val canRun: () -> Boolean,
    private val channelPlan: () -> JSONObject,
    private val captureSnapshot: () -> Unit,
    private val reviewCapture: () -> Unit
) : LinearLayout(context) {
    private val handler = Handler(Looper.getMainLooper())
    private val status = TextView(context)
    private val details = TextView(context)
    private val detailsButton = Button(context)
    private val button = Button(context)
    private val captureButton = Button(context)
    private val reviewButton = Button(context)
    private val captureStatus = TextView(context)
    private val captureReadiness = TextView(context)
    private val trend = LiveCellTrend()
    private val trendView = LiveCellTrendView(context)
    private val metricPanel = LiveCellMetricsPanel(context)
    private val changeButton = Button(context)
    private val changeStatus = TextView(context)
    private val changeEvents = TextView(context)
    private val changeExpand = Button(context)
    private var changeTracker: ServingCellChangeTracker? = null
    private var changeLogging = false
    private var changeExpanded = false
    private var changeIssue: String? = null
    private var active = false
    private var collectionBlocked = false
    private var generation = 0L
    private var requestId = 0L
    private var subscriptionId: Int? = null
    private var shownSubscriptionId: Int? = null
    private var fullDetails = ""
    private var detailsExpanded = false
    private var nextRequest: Runnable? = null
    private var timeout: Runnable? = null
    private var endSession: Runnable? = null
    private var responseReceivedAt: Long? = null
    private val freshnessTicker = object : Runnable {
        override fun run() {
            if (!active || responseReceivedAt == null) return
            status.text = LiveCellFreshness.describe(responseReceivedAt, SystemClock.elapsedRealtime()) ?: "Response timing unavailable."
            handler.postDelayed(this, 1000)
        }
    }
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private fun group(): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL
        setPadding(dp(14), dp(12), dp(14), dp(14))
        background = GradientDrawable().apply { setColor(Color.parseColor("#10212d")); cornerRadius = dp(14).toFloat() }
        this@LiveCellWorkspace.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(12) })
    }

    init {
        orientation = VERTICAL
        addView(TextView(context).apply {
            text = "Live cellular"; textSize = 17f; setTypeface(null, Typeface.BOLD)
            setTextColor(Color.parseColor("#edf5f8")); setPadding(0, dp(14), 0, dp(6))
        })
        addView(TextView(context).apply {
            text = "Foreground only · Requests every five seconds; Android may return cached or incomplete readings. Stops after five minutes; readings are not saved."
            textSize = 13f; setTextColor(Color.parseColor("#b4c8d1")); setPadding(0, 0, 0, dp(8))
        })
        button.apply { text = "Start live cellular"; styleFieldButton(primary = true); setOnClickListener { if (active) stop() else start() } }
        addView(button)
        status.apply { text = "Live monitor off. Choose a SIM and start when ready."; textSize = 13f; setTextColor(Color.parseColor("#b8cbd9")); setPadding(0, dp(5), 0, dp(5)) }
        details.apply { textSize = 13f; setTextColor(Color.parseColor("#e8f5fa")); setTextIsSelectable(true); setPadding(0, dp(5), 0, dp(10)); visibility = View.GONE }
        addView(status)
        metricPanel.visibility = View.GONE; addView(metricPanel)
        trendView.visibility = View.GONE; addView(trendView)
        addView(details)
        detailsButton.apply {
            text = "Show more cell reports"; styleFieldButton(); visibility = View.GONE
            setOnClickListener { detailsExpanded = !detailsExpanded; renderDetails() }
        }
        addView(detailsButton)
        val changes = group()
        changes.addView(TextView(context).apply {
            text = "Serving cell changes"; textSize = 15f; setTypeface(null, Typeface.BOLD)
            setTextColor(Color.parseColor("#edf5f8")); setPadding(0, 0, 0, dp(5))
        })
        changes.addView(TextView(context).apply {
            text = "Optional foreground log of reported LTE/NR identity changes. Times are response receipts, not exact transition times. This does not confirm a physical tower change or handover cause. Cleared when the live monitor stops."
            textSize = 12f; setTextColor(Color.parseColor("#b4c8d1")); setPadding(0, 0, 0, dp(7))
        })
        changeButton.apply {
            text = "Start cell change log"; styleFieldButton(); isEnabled = false
            setOnClickListener { toggleChangeLog() }
        }
        changes.addView(changeButton)
        changeStatus.apply { textSize = 12f; setTextColor(Color.parseColor("#b8cbd9")); setPadding(0, dp(4), 0, dp(4)) }
        changes.addView(changeStatus)
        changeEvents.apply { textSize = 13f; setTextColor(Color.parseColor("#e8f5fa")); setTextIsSelectable(true); visibility = View.GONE }
        changes.addView(changeEvents)
        changeExpand.apply {
            text = "Show all cell changes"; styleFieldButton(); visibility = View.GONE
            setOnClickListener { changeExpanded = !changeExpanded; renderChangeLog() }
        }
        changes.addView(changeExpand)
        renderChangeLog()
        val saved = group()
        saved.addView(TextView(context).apply {
            text = "Saved capture"; textSize = 15f; setTypeface(null, Typeface.BOLD)
            setTextColor(Color.parseColor("#edf5f8")); setPadding(0, 0, 0, dp(5))
        })
        saved.addView(TextView(context).apply {
            text = "A snapshot stops the live monitor and replaces the latest capture. Archive or export earlier evidence to keep it."
            textSize = 12f; setTextColor(Color.parseColor("#b4c8d1")); setPadding(0, 0, 0, dp(7))
        })
        captureButton.apply { text = "Take new snapshot"; styleFieldButton(); isEnabled = false; setOnClickListener { captureSnapshot() } }
        saved.addView(captureButton)
        captureReadiness.apply { textSize = 12f; setTextColor(Color.parseColor("#b8cbd9")); visibility = View.GONE }
        saved.addView(captureReadiness)
        captureStatus.apply { textSize = 13f; setTextColor(Color.parseColor("#b8cbd9")); visibility = View.GONE }
        saved.addView(captureStatus)
        reviewButton.apply { text = "Review latest saved capture"; styleFieldButton(); isEnabled = false; setOnClickListener { reviewCapture() } }
        saved.addView(reviewButton)
        addView(CellularReferencePanel(context))
    }

    fun setSnapshotReady(ready: Boolean, reason: CharSequence) {
        captureButton.isEnabled = ready
        captureReadiness.text = if (ready) "" else reason
        captureReadiness.visibility = if (ready || reason.isBlank()) View.GONE else View.VISIBLE
    }
    fun setCaptureAvailable(available: Boolean) { reviewButton.isEnabled = available }
    fun showCaptureStatus(message: CharSequence?) {
        captureStatus.text = message
        captureStatus.visibility = if (message.isNullOrBlank()) View.GONE else View.VISIBLE
    }

    /** Keep the first, serving-prioritized cell visible; fold additional reports. */
    private fun renderDetails() {
        val hasMore = fullDetails.contains("\n\n")
        details.text = if (detailsExpanded || !hasMore) fullDetails else fullDetails.substringBefore("\n\n")
        details.visibility = if (details.text.isNullOrBlank()) View.GONE else View.VISIBLE
        detailsButton.visibility = if (hasMore) View.VISIBLE else View.GONE
        detailsButton.text = if (detailsExpanded) "Show fewer cell reports" else "Show more cell reports"
        detailsButton.contentDescription = detailsButton.text
        detailsButton.isSelected = detailsExpanded
    }
    private fun clearDetails() { fullDetails = ""; detailsExpanded = false; renderDetails(); metricPanel.visibility = View.GONE; metricPanel.removeAllViews() }
    private fun clearFreshness() { handler.removeCallbacks(freshnessTicker); responseReceivedAt = null }

    private fun toggleChangeLog() {
        if (!active) return
        if (changeLogging) {
            changeLogging = false
        } else {
            val id = subscriptionId ?: return
            changeTracker = ServingCellChangeTracker(id.toString())
            changeLogging = true; changeExpanded = false; changeIssue = null
        }
        renderChangeLog()
    }

    private fun renderChangeLog() {
        val tracker = changeTracker
        val events = tracker?.events.orEmpty()
        changeButton.isEnabled = active
        changeButton.text = if (changeLogging) "Stop cell change log" else if (tracker == null) "Start cell change log" else "Start new cell change log"
        changeStatus.text = when {
            tracker == null -> if (active) "Start the change log when ready. Nothing is saved." else "Start the live monitor, then start the change log. Nothing is saved."
            changeLogging -> listOfNotNull(changeIssue, tracker.status, "${events.size} reported change(s) · up to 50 retained in memory.").joinToString("\n")
            else -> "Log stopped · ${events.size} reported change(s) retained until the live monitor stops."
        }
        val shown = events.asReversed().let { if (changeExpanded) it else it.take(5) }
        changeEvents.text = shown.joinToString("\n\n", transform = CellChangeLogText::event)
        changeEvents.visibility = if (shown.isEmpty()) View.GONE else View.VISIBLE
        changeExpand.visibility = if (events.size > 5) View.VISIBLE else View.GONE
        changeExpand.text = if (changeExpanded) "Show recent cell changes" else "Show all ${events.size} cell changes"
        changeExpand.contentDescription = changeExpand.text
    }

    private fun breakChangeContinuity(id: Int, now: Long, message: String) {
        if (!changeLogging) return
        changeTracker?.accept(id.toString(), emptyList(), now, Instant.now().toString())
        changeIssue = message
        renderChangeLog()
    }

    fun selectionChanged() {
        val selected = selectedSubscriptionId()
        if (active && selected != subscriptionId) stop("SIM changed. Start the live monitor again for the selected SIM.")
        if (shownSubscriptionId != selected) { clearDetails(); shownSubscriptionId = null }
    }
    fun setCollectionBlocked(blocked: Boolean) {
        collectionBlocked = blocked
        if (blocked && active) stop("Live monitor stopped while another capture or Desktop session is active.")
        if (blocked) { clearDetails(); shownSubscriptionId = null }
        button.isEnabled = !blocked
    }
    fun stop(message: String = "Live monitor stopped. No readings were saved.") {
        if (!active) return
        active = false; generation++; requestId++; subscriptionId = null
        nextRequest?.let(handler::removeCallbacks); timeout?.let(handler::removeCallbacks); endSession?.let(handler::removeCallbacks)
        nextRequest = null; timeout = null; endSession = null
        clearFreshness(); clearDetails(); shownSubscriptionId = null
        trend.reset(); trendView.show(trend); trendView.visibility = View.GONE
        changeTracker = null; changeLogging = false; changeExpanded = false; changeIssue = null; renderChangeLog()
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
        renderChangeLog()
        button.text = "Stop live cellular"; status.text = "Requesting a cell update…"; clearFreshness(); clearDetails(); shownSubscriptionId = null
        trend.reset(); trendView.show(trend); trendView.visibility = View.VISIBLE
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
                breakChangeContinuity(id, now, "Cell response unavailable; no change was inferred across the gap.")
                clearFreshness()
                status.text = "$error · retrying while this screen remains open."
                clearDetails(); shownSubscriptionId = null
                trend.reset("Cell response unavailable; history cleared."); trendView.show(trend)
            } else {
                val values = cells.orEmpty().take(MAX_CELLS).mapNotNull { runCatching { CellularSnapshot.cell(it, now) }.getOrNull() }
                if (changeLogging) {
                    if (cells == null || cells.size > MAX_CELLS || values.size != cells.size) {
                        breakChangeContinuity(id, now, "Cell response incomplete; no change was inferred across the gap.")
                    } else {
                        changeIssue = null
                        changeTracker?.accept(id.toString(), values, now, Instant.now().toString())
                        renderChangeLog()
                    }
                }
                trend.accept(values, now); trendView.show(trend)
                metricPanel.show(runCatching { LiveCellMetrics.build(values, channelPlan()) }.getOrNull())
                metricPanel.visibility = View.VISIBLE
                val rendered = runCatching { LiveCellSummary.render(values, channelPlan()) }.getOrElse { "Cell details are unavailable for this response." }
                val omitted = (cells.orEmpty().size - values.size).coerceAtLeast(0)
                clearFreshness(); responseReceivedAt = now; freshnessTicker.run()
                fullDetails = rendered + if (omitted > 0) "\n\n$omitted reports omitted or unreadable." else ""
                renderDetails()
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

    private companion object { const val MIN_INTERVAL_MS = 5_000L; const val TIMEOUT_MS = 12_000L; const val MAX_DURATION_MS = 300_000L; const val MAX_CELLS = 256 }
}
