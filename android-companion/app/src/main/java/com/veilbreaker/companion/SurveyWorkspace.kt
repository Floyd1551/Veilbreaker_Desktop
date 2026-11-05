package com.veilbreaker.companion

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import org.json.JSONObject
import java.time.Instant

/** Local survey workspace; no automatic collection, scoring, or synthetic coordinates. */
class SurveyWorkspace(context: Context, private val captureProvider: () -> JSONObject?) : LinearLayout(context) {
    private val activity = context as Activity
    private val store = MobileSurveyStore(context)
    private val handler = Handler(Looper.getMainLooper())
    private val content = LinearLayout(context)
    private var listing = MobileSurveyStore.Listing(emptyList(), 0)
    private var current: JSONObject? = null
    private var busy = false
    private var externalEnabled = true
    private var pendingExport: ByteArray? = null
    private var message = "Loading local surveys…"
    private var requestedName = ""
    private var creating = false
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()

    init {
        orientation = VERTICAL
        val scroll = ScrollView(context).apply { isFillViewport = true }
        content.orientation = VERTICAL
        content.setPadding(0, dp(4), 0, dp(16))
        scroll.addView(content); addView(scroll, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        render(); reloadList()
    }

    fun refresh() { render() }

    /** The host disables document pickers and capture attachment during a USB session or pending capture. */
    fun setExternalActionsEnabled(enabled: Boolean) {
        if (externalEnabled == enabled) return
        externalEnabled = enabled; render()
    }

    private fun text(parent: LinearLayout, value: String, size: Float = 14f, bright: Boolean = false): TextView = TextView(context).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(if (bright) "#e8f5fa" else "#aabfce"))
        if (bright) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(4), 0, dp(5)); parent.addView(this)
    }

    private fun card(title: String): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL; setPadding(dp(14), dp(11), dp(14), dp(13))
        background = GradientDrawable().apply { setColor(Color.parseColor("#112335")); cornerRadius = dp(12).toFloat(); setStroke(dp(1), Color.parseColor("#294052")) }
        content.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(10) })
        text(this, title, 16f, true)
    }

    private fun button(parent: LinearLayout, title: String, enabled: Boolean = true, action: () -> Unit): Button = Button(context).apply {
        text = title; isAllCaps = false; minHeight = dp(48); isEnabled = enabled && !busy
        backgroundTintList = android.content.res.ColorStateList.valueOf(Color.parseColor("#213e56"))
        setTextColor(Color.parseColor("#e5f5fa")); setOnClickListener { action() }; parent.addView(this)
    }

    private fun render() {
        content.removeAllViews()
        text(content, "PHONE SURVEYS", 12f, true).setTextColor(Color.parseColor("#63d6ee"))
        if (message.isNotBlank()) text(content, message, 12f)
        val survey = current
        if (survey == null) {
            if (creating) {
                val create = card("New survey")
                text(create, "Group up to 20 saved captures. Adding a point does not start collection.", 12f)
                val name = EditText(context).apply {
                    hint = "Survey name"; contentDescription = "Survey name"; setSingleLine(true)
                    isEnabled = !busy
                    setTextColor(Color.WHITE); setHintTextColor(Color.LTGRAY)
                    filters = arrayOf(android.text.InputFilter.LengthFilter(80)); setText(requestedName)
                    addTextChangedListener(object : TextWatcher {
                        override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) { }
                        override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { requestedName = s?.toString() ?: "" }
                        override fun afterTextChanged(s: Editable?) { }
                    })
                }
                create.addView(name)
                button(create, "Create survey") {
                    val nameToCreate = name.text.toString()
                    requestedName = nameToCreate
                    runJob({
                        val made = MobileSurvey.create(nameToCreate, Instant.now().toString())
                        store.save(made); made
                    }) { made -> current = made; creating = false; requestedName = ""; message = "Survey created on this phone." }
                }
                button(create, "Cancel") { creating = false; message = ""; render() }
            } else {
                val list = card("Saved on this phone · ${listing.surveys.size}")
                if (listing.surveys.isEmpty()) text(list, "No mobile surveys yet.", 13f)
                for (row in listing.surveys) button(list, "${row.name}\n${row.state} · ${row.count}/20 captures") {
                    runJob({ store.load(row.id) }) { loaded -> current = loaded; message = "Opened phone-only survey." }
                }
                if (listing.unavailable > 0) text(list, "${listing.unavailable} survey file(s) could not be read; they were preserved.")
                button(list, "New survey") { creating = true; message = ""; render() }
            }
            return
        }
        val state = survey.getString("lifecycle"); val points = survey.getJSONArray("points")
        val summary = card(survey.getString("name"))
        text(summary, "${state.uppercase()} · ${points.length()}/20 captures · Created ${survey.getString("created_utc")}")
        if (!externalEnabled) text(summary, "Stop the active Desktop session or capture before adding or exporting.")
        button(summary, "Add last phone capture", externalEnabled && state == "open") {
            val selected = captureProvider()
            if (selected == null) { message = "Capture on the phone first, then return here to add it."; render() }
            else runJob({
                val updated = MobileSurvey.addCapture(survey, selected, Instant.now().toString())
                store.save(updated); updated
            }) { updated -> current = updated; message = "Capture added as a separate survey point." }
        }
        if (state == "open") button(summary, "Complete survey") {
            runJob({ val updated = MobileSurvey.complete(survey, Instant.now().toString()); store.save(updated); updated }) {
                current = it; message = "Survey completed. Reopen it to add captures."
            }
        } else button(summary, "Reopen survey") {
            runJob({ val updated = MobileSurvey.reopen(survey); store.save(updated); updated }) { current = it; message = "Survey reopened." }
        }
        button(summary, "Export mobile survey JSON…", externalEnabled) { prepareExport(survey) }
        button(summary, "View survey locations", externalEnabled) {
            if (!externalEnabled) return@button
            try {
                activity.startActivity(Intent(context, GpsMapActivity::class.java).putExtra("mobile_survey_id", survey.getString("survey_id")))
            } catch (_: Exception) { message = "Unable to open the GPS view."; render() }
        }
        text(summary, "Export contains original phone captures and may include identifiers and location. Desktop survey import is not yet supported.", 12f)
        button(summary, "Delete survey…") {
            val surveyId = survey.getString("survey_id")
            AlertDialog.Builder(context).setTitle("Delete mobile survey?")
                .setMessage("Permanently delete this survey and its copied captures? The phone's last capture and other surveys are kept.")
                .setNegativeButton("Cancel", null)
                .setPositiveButton("Delete") { _, _ ->
                    runJob({ store.delete(surveyId); runCatching { store.list() }.getOrNull() }) { updated ->
                        current = null
                        listing = updated ?: listing.copy(surveys = listing.surveys.filterNot { it.id == surveyId })
                        message = "Mobile survey deleted. Other surveys and the last capture were kept."
                    }
                }.show()
        }
        button(summary, "All surveys") { current = null; message = "Choose a survey or create one."; reloadList() }
        val pointCard = card("Captured points")
        if (points.length() == 0) text(pointCard, "No points yet. Capture on the phone, then add the saved capture.")
        for (i in 0 until points.length()) {
            val point = points.getJSONObject(i); val capture = point.getJSONObject("capture")
            val fixes = GpsSpatialModel.savedFixes(capture); val lastFix = fixes.lastOrNull()
            val location = if (lastFix == null) "No usable GPS fix" else {
                val age = lastFix.ageAtReceiptMs?.let { "${it / 1000}s old at receipt" } ?: "age unavailable"
                "Last reported fix: ${lastFix.latitude}, ${lastFix.longitude} · ±${lastFix.accuracy} m · $age" + if (lastFix.mock) " · mock" else ""
            }
            text(pointCard, "${i + 1}. ${capture.optString("created_utc", "Time unavailable")}\n$location", 13f, true)
            text(pointCard, MobileSurvey.signalSummary(capture), 12f)
            text(pointCard, "Capture ${capture.getString("capture_id")} · ${capture.getJSONObject("collection").optString("outcome")} · added ${point.getString("attached_utc")}", 12f)
        }
    }

    private fun <T> runJob(work: () -> T, done: (T) -> Unit) {
        if (busy) return
        busy = true; render()
        Thread {
            val result = runCatching(work)
            handler.post {
                if (activity.isFinishing || activity.isDestroyed) return@post
                busy = false
                result.fold(done, { error -> message = error.message ?: "The survey operation could not be completed." })
                render()
            }
        }.apply { name = "Veilbreaker mobile survey"; start() }
    }

    private fun reloadList() {
        runJob({ store.list() }) { result -> listing = result; message = "" }
    }

    private fun prepareExport(survey: JSONObject) {
        if (!externalEnabled || busy) return
        runJob({ MobileSurvey.validate(survey).toString().toByteArray(Charsets.UTF_8) }) { bytes ->
            if (!externalEnabled) { message = "Stop the active Desktop session or capture before exporting."; return@runJob }
            pendingExport = bytes
            try {
                @Suppress("DEPRECATION")
                activity.startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE); type = "application/json"
                    putExtra(Intent.EXTRA_TITLE, "veilbreaker-mobile-survey.json")
                }, EXPORT_REQUEST)
                message = "Choose where to save the mobile survey JSON."
            } catch (_: Exception) { pendingExport = null; message = "Could not open the document picker." }
        }
    }

    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode != EXPORT_REQUEST) return false
        val bytes = pendingExport; pendingExport = null
        if (resultCode != Activity.RESULT_OK || data?.data == null || bytes == null) {
            message = "Survey export cancelled; the saved survey is unchanged."; render(); return true
        }
        val uri = data.data!!
        runJob({ activity.contentResolver.openOutputStream(uri, "wt")?.use { it.write(bytes) }
            ?: throw IllegalArgumentException("Could not write the selected document.") }) {
            message = "Mobile survey JSON exported. Desktop survey import is not yet supported."
        }
        return true
    }

    companion object { const val EXPORT_REQUEST = 72 }
}
