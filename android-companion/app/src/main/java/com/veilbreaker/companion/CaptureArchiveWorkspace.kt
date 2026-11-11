package com.veilbreaker.companion

import android.app.Activity
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.os.Handler
import android.os.Looper
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject

/** Explicitly managed copies; viewing or deleting one never changes the current capture. */
class CaptureArchiveWorkspace(
    private val activity: Activity,
    private val currentCapture: () -> JSONObject?,
    private val channelPlan: () -> JSONObject,
    private val exportJson: (JSONObject) -> Unit,
    private val exportPdf: (JSONObject) -> Unit
) : LinearLayout(activity) {
    private val store = MobileCaptureArchiveStore(activity)
    private val handler = Handler(Looper.getMainLooper())
    private val body = LinearLayout(activity)
    private var captures = emptyList<JSONObject>()
    private var busy = false
    private var loaded = false
    private var expanded = false
    private var externalEnabled = true
    private var message = ""
    private var reportId: String? = null
    private var reportText: String? = null
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    init { orientation = VERTICAL; body.orientation = VERTICAL; addView(body); reload() }

    fun setExternalEnabled(enabled: Boolean) { externalEnabled = enabled; render() }
    private fun text(value: String, size: Float = 13f, bold: Boolean = false) = TextView(context).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(if (bold) "#e8f5fa" else "#b8cbd9"))
        if (bold) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(4), 0, dp(4))
    }
    private fun action(parent: LinearLayout, title: String, enabled: Boolean = true, click: () -> Unit) {
        parent.addView(Button(context).apply {
            text = title; isAllCaps = false; minHeight = dp(48); isEnabled = enabled && !busy
            backgroundTintList = ColorStateList(arrayOf(intArrayOf(-android.R.attr.state_enabled), intArrayOf()),
                intArrayOf(Color.parseColor("#1b2935"), Color.parseColor("#213e56")))
            setTextColor(ColorStateList(arrayOf(intArrayOf(-android.R.attr.state_enabled), intArrayOf()),
                intArrayOf(Color.parseColor("#8ca0ae"), Color.WHITE)))
            setOnClickListener { click() }
        }, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
    }
    private fun <T> runJob(work: () -> T, done: (T) -> Unit) {
        if (busy) return
        busy = true; render()
        Thread {
            val result = runCatching(work)
            handler.post {
                if (activity.isFinishing || activity.isDestroyed) return@post
                busy = false
                result.fold(done, { message = it.message ?: "Archive operation failed; saved captures are unchanged." })
                render()
            }
        }.apply { name = "Veilbreaker capture archive"; start() }
    }
    private fun reload() = runJob({ runCatching { store.list() } }) { result ->
        result.fold({ captures = it; loaded = true; message = "" }, {
            loaded = false; message = "Could not read the archive. Saved copies may still exist; try refreshing."
        })
    }
    private fun render() {
        body.removeAllViews()
        body.addView(text("SAVED CAPTURE COPIES", 16f, true))
        action(body, if (expanded) "Hide capture archive" else "Open capture archive") { expanded = !expanded; render() }
        if (!expanded) {
            body.addView(text(if (busy) "Checking archive…" else if (loaded) "${captures.size} saved capture copies" else "Archive status unavailable; open to retry.", 12f))
            return
        }
        body.addView(text("Save up to 20 captures on this phone. Copies stay separate from the latest capture and surveys; export important evidence for backup.", 12f))
        action(body, "Save latest capture to archive", loaded && currentCapture() != null && externalEnabled) {
            val snapshot = currentCapture()?.toString() ?: return@action
            runJob({ store.add(JSONObject(snapshot)) }) { captures = it; message = "Capture copy saved in the archive." }
        }
        action(body, "Refresh saved captures") { reload() }
        if (busy) body.addView(text("Working…", 12f))
        if (message.isNotBlank()) body.addView(text(message, 12f))
        if (!externalEnabled) body.addView(text("Stop the current capture or Desktop session to save or export.", 12f))
        if (loaded && captures.isEmpty() && !busy) body.addView(text("No archived captures. Save the latest capture to keep a separate copy.", 12f))
        (if (loaded) captures.asReversed() else emptyList()).forEach { capture ->
            val id = capture.optString("capture_id")
            val section = LinearLayout(context).apply { orientation = VERTICAL; setPadding(dp(10), dp(8), dp(10), dp(8)) }
            body.addView(section, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            section.addView(text("${capture.optString("created_utc", "Time unavailable")} · ${capture.optJSONObject("collection")?.optString("outcome") ?: "unknown"}", 14f, true))
            section.addView(text("Capture $id", 12f))
            action(section, if (reportId == id && reportText != null) "Hide saved report" else "View saved report") {
                if (reportId == id && reportText != null) { reportId = null; reportText = null; render() }
                else runJob({ CaptureReportContent.build(capture, channelPlan()) }) { value -> reportId = id; reportText = value; message = "" }
            }
            if (reportId == id && reportText != null) {
                val content = reportText.orEmpty()
                section.addView(text(content.take(16000) + if (content.length > 16000) "\n[Preview truncated; export JSON for complete captured evidence.]" else "", 12f))
            }
            action(section, "Export saved JSON…", externalEnabled) { exportJson(capture) }
            action(section, "Export saved PDF…", externalEnabled) { exportPdf(capture) }
            action(section, "Delete archived copy") {
                AlertDialog.Builder(context).setTitle("Delete archived copy?")
                    .setMessage("This deletes only this archive copy. The latest capture, exports and survey copies are unchanged.")
                    .setNegativeButton("Cancel", null).setPositiveButton("Delete") { _, _ ->
                        runJob({ store.remove(id) }) { result ->
                            captures = result; if (reportId == id) { reportId = null; reportText = null }
                            message = "Archived copy deleted."
                        }
                    }.show()
            }
        }
    }
}
