package com.veilbreaker.companion

import android.app.Activity
import android.app.AlertDialog
import android.content.Context
import android.content.Intent
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.os.Bundle
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
class SurveyWorkspace(
    context: Context,
    private val captureProvider: () -> JSONObject?,
    private val requestCapture: ((Result<JSONObject>) -> Unit) -> Unit,
    private val cancelCapture: () -> Unit,
    private val restoredState: Bundle? = null
) : LinearLayout(context) {
    private val activity = context as Activity
    private val store = MobileSurveyStore(context)
    private val archiveStore = MobileCaptureArchiveStore(context)
    private val handler = Handler(Looper.getMainLooper())
    private val content = LinearLayout(context)
    private val scroll = ScrollView(context)
    private var listing = MobileSurveyStore.Listing(emptyList(), 0)
    private var current: JSONObject? = null
    private var busy = false
    private var capturing = false
    private var captureGeneration = 0
    private var externalEnabled = true
    private val exportStore = PendingSurveyExportStore(java.io.File(context.filesDir, "pending-survey-exports"))
    private var pendingDocument: PendingSurveyExportStore.Reference? = null
    private var exportMonitorToken: String? = null
    private var exportMessage = ""
    private var preparingExport = false
    private var report: MobileSurveyReport.Report? = null
    private var showMoreActions = false
    private var showAllPoints = false
    private val noteDrafts = mutableMapOf<String, String>()
    private var message = "Loading local surveys…"
    private var requestedName = ""
    private var creating = false
    private var restoringSurveyId: String? = null
    private var creatingSurveyId: String? = null
    private var deletingSurveyId: String? = null
    private var restorePendingDeletion = false
    private var restoreInterruptedCapture = false
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()

    init {
        orientation = VERTICAL
        scroll.isFillViewport = true
        content.orientation = VERTICAL
        content.setPadding(0, dp(4), 0, dp(16))
        scroll.addView(content); addView(scroll, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.MATCH_PARENT))
        creating = restoredState?.getBoolean("creating") ?: false
        requestedName = restoredState?.getString("name").orEmpty().take(80)
        showMoreActions = restoredState?.getBoolean("more_actions") ?: false
        showAllPoints = restoredState?.getBoolean("all_points") ?: false
        pendingDocument = PendingSurveyExportStore.reference(
            restoredState?.getString("export_token"), restoredState?.getString("export_sha256"),
            restoredState?.getString("export_kind"))
        exportMessage = restoredState?.getString("export_message").orEmpty().take(500)
        if (restoredState?.getBoolean("export_preparing") == true && pendingDocument == null)
            exportMessage = "Export preparation was interrupted. Choose Export again; the saved survey is unchanged."
        restoringSurveyId = restoredState?.getString("survey_id")?.takeIf { Regex("[a-f0-9-]{36}").matches(it) }
        restorePendingDeletion = restoredState?.getBoolean("survey_deleting") ?: false
        restoreInterruptedCapture = restoredState?.getBoolean("capture_interrupted") ?: false
        val drafts = restoredState?.getBundle("note_drafts")
        drafts?.keySet()?.take(MobileSurvey.MAX_POINTS)?.forEach { id ->
            drafts.getString(id)?.takeIf { it.length <= 500 }?.let { noteDrafts[id] = it }
        }
        render()
        val id = restoringSurveyId
        if (id == null) reloadList() else restoreSurvey(id)
        monitorPendingExport()
    }

    fun refresh() { render() }

    /** Save only navigation and bounded unsaved text, never a second copy of captured evidence. */
    fun saveState(): Bundle = Bundle().apply {
        putString("survey_id", current?.optString("survey_id") ?: restoringSurveyId ?: creatingSurveyId)
        putBoolean("creating", creating); putString("name", requestedName)
        putBoolean("survey_deleting", deletingSurveyId != null || restorePendingDeletion)
        putBoolean("capture_interrupted", capturing || restoreInterruptedCapture)
        putBoolean("more_actions", showMoreActions); putBoolean("all_points", showAllPoints)
        pendingDocument?.let { putString("export_token", it.token); putString("export_sha256", it.sha256); putString("export_kind", it.kind) }
        putString("export_message", exportMessage.take(500))
        putBoolean("export_preparing", preparingExport)
        putBundle("note_drafts", Bundle().apply { noteDrafts.forEach { (id, note) -> putString(id, note) } })
    }

    private fun restoreSurvey(id: String) {
        runJob({ pendingWrites.await(id); if (store.exists(id)) store.load(id) else null }) { loaded ->
            if (loaded == null) {
                if (restorePendingDeletion || creating) {
                    restoringSurveyId = null
                    if (restorePendingDeletion) {
                        noteDrafts.clear(); creating = false
                        message = "Survey is no longer available. Other surveys and the last capture were kept."
                        runJob({ pendingWrites.awaitAll(); store.list() }) { listing = it }
                    } else {
                        message = "Survey creation did not finish. Check the name and try again."
                    }
                    restorePendingDeletion = false
                } else {
                    message = "The survey is unavailable. Drafts are retained; retry or return to surveys."
                }
                return@runJob
            }
            restoringSurveyId = null
            current = loaded
            val deletionWasPending = restorePendingDeletion
            val creationWasPending = creating
            creating = false; requestedName = ""; restorePendingDeletion = false
            val points = loaded.getJSONArray("points")
            val savedNotes = (0 until points.length()).associate { index ->
                val point = points.getJSONObject(index)
                point.getJSONObject("capture").getString("capture_id") to (point.opt("operator_note") as? String)
            }
            val validDrafts = SurveyDraftState.reconcile(noteDrafts, savedNotes)
            noteDrafts.clear(); noteDrafts.putAll(validDrafts)
            if (noteDrafts.isNotEmpty()) showAllPoints = true
            message = when {
                deletionWasPending -> "Deletion may not have completed. The survey is still present; check it before trying again."
                creationWasPending -> "Survey creation completed; the saved survey is open."
                noteDrafts.isNotEmpty() -> "Survey view restored. Unsaved operator notes are available by editing their points."
                else -> "Survey view restored."
            }
            if (deletionWasPending && noteDrafts.isNotEmpty()) message += " Unsaved note drafts are still available."
            if (restoreInterruptedCapture) {
                message += " Capture may have been interrupted. Check the survey and the last saved capture before retrying."
                restoreInterruptedCapture = false
            }
        }
    }

    /** The host disables document pickers and capture attachment during a USB session or pending capture. */
    fun setExternalActionsEnabled(enabled: Boolean) {
        if (externalEnabled == enabled) return
        externalEnabled = enabled; render()
    }

    private fun text(parent: LinearLayout, value: String, size: Float = 14f, bright: Boolean = false): TextView = TextView(context).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(if (bright) "#e8f3fa" else "#b1c5d3"))
        if (bright) setTypeface(null, Typeface.BOLD)
        setLineSpacing(dp(2).toFloat(), 1f)
        setPadding(0, dp(3), 0, dp(4)); parent.addView(this)
    }

    private fun card(title: String): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL; setPadding(dp(14), dp(12), dp(14), dp(14))
        background = GradientDrawable().apply { setColor(Color.parseColor("#0d1e2c")); cornerRadius = dp(10).toFloat(); setStroke(dp(1), Color.parseColor("#263e50")) }
        content.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(10) })
        text(this, title, 16f, true)
    }

    private fun button(parent: LinearLayout, title: String, enabled: Boolean = true, primary: Boolean = false, action: () -> Unit): Button = Button(context).apply {
        text = title; isAllCaps = false; minHeight = dp(48); isEnabled = enabled && !busy && !capturing
        textSize = 14f
        setTypeface(null, Typeface.BOLD)
        background = GradientDrawable().apply { cornerRadius = dp(8).toFloat(); setColor(Color.WHITE) }
        val states = arrayOf(intArrayOf(-android.R.attr.state_enabled), intArrayOf())
        backgroundTintList = ColorStateList(states, intArrayOf(Color.parseColor("#1a2c3a"), Color.parseColor(if (primary) "#58d5eb" else "#1c374b")))
        setTextColor(ColorStateList(states, intArrayOf(Color.parseColor("#93a8b6"), Color.parseColor(if (primary) "#08202b" else "#e5f5fa"))))
        setOnClickListener { action() }
        parent.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(5) })
    }

    private fun render() {
        content.removeAllViews()
        text(content, "PHONE SURVEYS", 12f, true).apply {
            setTextColor(Color.parseColor("#65d7ea")); letterSpacing = 0.08f
        }
        if (message.isNotBlank()) text(content, message, 12f).apply {
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = GradientDrawable().apply { setColor(Color.parseColor("#102a3a")); cornerRadius = dp(7).toFloat(); setStroke(dp(1), Color.parseColor("#284657")) }
        }
        if (exportMessage.isNotBlank()) text(content, exportMessage, 12f).apply {
            setPadding(dp(10), dp(8), dp(10), dp(8))
            background = GradientDrawable().apply { setColor(Color.parseColor("#102a3a")); cornerRadius = dp(7).toFloat(); setStroke(dp(1), Color.parseColor("#284657")) }
        }
        pendingDocument?.let { pending ->
            val export = card("Pending survey export")
            val writing = exportOperations.status(pending.token)?.running == true
            text(export, if (writing) "Saving the verified snapshot…" else "The original export snapshot is retained. If a previous save was interrupted, check its destination before retrying.", 12f)
            button(export, "Choose destination again…", externalEnabled && !writing) { openDocument(pending) }
            button(export, "Discard pending export", !writing) {
                try { exportStore.remove(pending) } catch (_: Exception) { }
                pendingDocument = null; exportMessage = "Pending export discarded; the saved survey is unchanged."; render()
            }
        }
        val survey = current
        if (survey == null) {
            val restoreId = restoringSurveyId
            if (restoreId != null) {
                val restore = card("Reopening survey")
                text(restore, "Unsaved operator notes remain drafts until you choose Save. They are not measurements.", 12f)
                button(restore, "Retry opening survey") { restoreSurvey(restoreId) }
                button(restore, "Discard drafts and return to surveys") {
                    restoringSurveyId = null; noteDrafts.clear(); message = "Choose a survey or create one."; reloadList()
                }
                return
            }
            if (creating) {
                val create = card("New survey")
                text(create, "Group up to 20 captures. Capture a new point or add a previously saved phone capture.", 12f)
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
                button(create, "Create survey", primary = true) {
                    val nameToCreate = name.text.toString()
                    requestedName = nameToCreate
                    val made = try { MobileSurvey.create(nameToCreate, Instant.now().toString()) }
                        catch (error: Exception) { message = error.message ?: "Invalid survey name."; render(); return@button }
                    val id = made.getString("survey_id")
                    creatingSurveyId = id
                    if (!runSurveyMutation(id, { runCatching { store.save(made); made } }) { result ->
                        creatingSurveyId = null
                        result.fold({ saved ->
                            current = saved; showMoreActions = false; showAllPoints = false
                            creating = false; requestedName = ""; message = "Survey created on this phone."
                        }, { error -> message = error.message ?: "Survey could not be created." })
                    }) creatingSurveyId = null
                }
                button(create, "Cancel") { creating = false; message = ""; render() }
            } else {
                val list = card("Saved on this phone · ${listing.surveys.size}")
                if (listing.surveys.isEmpty()) text(list, "No mobile surveys yet.", 13f)
                for (row in listing.surveys) button(list, "${row.name}\n${row.state} · ${row.count}/20 captures") {
                    runJob({ store.load(row.id) }) { loaded -> current = loaded; showMoreActions = false; showAllPoints = false; message = "Opened phone-only survey." }
                }
                if (listing.unavailable > 0) text(list, "${listing.unavailable} survey file(s) could not be read; they were preserved.")
                button(list, "New survey", primary = true) { creating = true; message = ""; render() }
            }
            return
        }
        val state = survey.getString("lifecycle"); val points = survey.getJSONArray("points")
        val reviewed = report
        if (reviewed != null) {
            val heading = card("Survey dashboard · ${reviewed.name}")
            text(heading, "${reviewed.points.size} captures · ${reviewed.completeCount} complete · ${reviewed.partialCount} partial\n${reviewed.lifecycle.uppercase()} · Created ${reviewed.createdUtc}", 14f, true)
            text(heading, "Values are saved observations, not live. Compare the same technology, subscription, carrier, band and cell where exposed; different sources may not be directly comparable. Cell and location times can differ.", 12f)
            button(heading, "Export survey report HTML…", externalEnabled && pendingDocument == null) { prepareReportExport(reviewed) }
            text(heading, "The report can contain cell identifiers and location. Export survey JSON separately to retain the original captures.", 12f)
            button(heading, "Back to survey") { report = null; render(); scroll.post { scroll.scrollTo(0, 0) } }
            if (reviewed.points.isEmpty()) text(heading, "No captures are saved in this survey.", 12f)
            for (point in reviewed.points) {
                val item = card("Point ${point.number} · ${point.outcome.uppercase()}")
                text(item, "Captured ${point.createdUtc}\nCapture ${point.captureId}", 12f)
                text(item, point.location, 12f, true)
                reviewed.locations[point.number]?.let { text(item, "Last reported receiver coordinates: ${it.latitude}, ${it.longitude}", 12f) }
                point.operatorNote?.let { text(item, "Operator observation · not a measured value\n$it", 12f) }
                if (point.servingCells.isEmpty()) text(item, "No registered serving cell reported in the latest observations.", 12f)
                for (cell in point.servingCells) {
                    text(item, "${cell.radio} · ${cell.role} · ${cell.subscription}\n${cell.carrier} · ${cell.band}", 13f, true)
                    text(item, "${cell.age} · observation assembled ${cell.received}", 12f)
                    cell.cellResponseReceived?.let { text(item, "Cell response received $it · location may have been acquired separately", 12f) }
                    text(item, cell.identity.joinToString(" · "), 12f)
                    text(item, cell.metrics.joinToString(" · "), 12f)
                }
                if (point.omittedServing > 0) text(item, "${point.omittedServing} additional serving cell(s) not displayed.", 12f)
                if (point.inventoryIncomplete) text(item, "Some cell or observation data exceeds the review limit. Shown cells may not be latest; inspect the original capture.", 12f)
            }
            return
        }
        val summary = card(survey.getString("name"))
        text(summary, "${state.uppercase()} · ${points.length()}/20 captures · Created ${survey.getString("created_utc")}")
        if (state != "open") text(summary, "This survey is complete. Open More survey actions to reopen it before adding points.", 12f)
        button(summary, "All surveys") {
            fun leave() {
                current = null; noteDrafts.clear(); showMoreActions = false; showAllPoints = false
                message = "Choose a survey or create one."; reloadList(); scroll.post { scroll.scrollTo(0, 0) }
            }
            if (noteDrafts.isEmpty()) leave() else AlertDialog.Builder(context)
                .setTitle("Discard unsaved notes?")
                .setMessage("Unsaved operator note drafts will be discarded. Saved survey data is unchanged.")
                .setNegativeButton("Keep editing", null)
                .setPositiveButton("Discard drafts") { _, _ -> leave() }.show()
        }
        if (capturing) {
            text(summary, "Capturing a new point. Keep Veilbreaker in the foreground. GPS acquisition may take up to 30 seconds; partial results will be identified.")
            summary.addView(Button(context).apply {
                text = "Cancel capture"; styleFieldButton()
                setOnClickListener {
                    if (!capturing) return@setOnClickListener
                    captureGeneration++; capturing = false
                    message = "Capture cancelled. Survey unchanged; any already saved phone capture is retained."
                    try { cancelCapture() } catch (_: Exception) { }
                    render()
                }
            })
        } else if (!externalEnabled) text(summary, "Stop the active Desktop session or capture before adding or exporting.")
        button(summary, "Capture and add point", externalEnabled && state == "open" && points.length() < MobileSurvey.MAX_POINTS, primary = true) {
            startCaptureAndAdd(survey.getString("survey_id"))
        }
        button(summary, "Add last phone capture", externalEnabled && state == "open" && points.length() < MobileSurvey.MAX_POINTS) {
            val selected = captureProvider()
            if (selected == null) { message = "Capture on the phone first, then return here to add it."; render() }
            else runSurveyMutation(survey.getString("survey_id"), {
                store.update(survey.getString("survey_id")) { latest -> MobileSurvey.addCapture(latest, selected, Instant.now().toString()) }
            }) { updated -> current = updated; message = "Capture added as a separate survey point." }
        }
        button(summary, "Add archived capture…", externalEnabled && state == "open" && points.length() < MobileSurvey.MAX_POINTS) {
            pickArchivedCapture(survey.getString("survey_id"))
        }
        text(summary, "Archived captures are copied into the survey; the archive and latest phone capture stay unchanged.", 12f)
        if (state == "open" && points.length() >= MobileSurvey.MAX_POINTS) text(summary, "This survey already has 20 captures.", 12f)
        button(summary, "View survey locations", externalEnabled) {
            if (!externalEnabled) return@button
            try {
                activity.startActivity(Intent(context, GpsMapActivity::class.java).putExtra("mobile_survey_id", survey.getString("survey_id")))
            } catch (_: Exception) { message = "Unable to open the GPS view."; render() }
        }
        button(summary, "View survey dashboard & report") {
            val snapshot = JSONObject(survey.toString())
            runJob({
                val plan = try { JSONObject(context.assets.open("channel-bands.json").bufferedReader().use { it.readText() }) } catch (_: Exception) { null }
                MobileSurveyReport.build(snapshot, plan)
            }) { report = it; message = ""; scroll.post { scroll.scrollTo(0, 0) } }
        }
        button(summary, if (showMoreActions) "Fewer survey actions ▲" else "More survey actions ▾") {
            showMoreActions = !showMoreActions; render()
        }.apply { contentDescription = if (showMoreActions) "Hide additional survey actions" else "Show additional survey actions" }
        if (showMoreActions) {
            if (state == "open") button(summary, "Complete survey") {
                if (noteDrafts.isNotEmpty()) {
                    message = "Save or discard unsaved operator notes before completing the survey."; showAllPoints = true; render()
                } else runSurveyMutation(survey.getString("survey_id"), { store.update(survey.getString("survey_id")) { latest -> MobileSurvey.complete(latest, Instant.now().toString()) } }) {
                    current = it; message = "Survey completed. Reopen it to add captures."
                }
            } else button(summary, "Reopen survey") {
                runSurveyMutation(survey.getString("survey_id"), { store.update(survey.getString("survey_id")) { latest -> MobileSurvey.reopen(latest) } }) { current = it; message = "Survey reopened." }
            }
            button(summary, "Export mobile survey JSON…", externalEnabled && pendingDocument == null) { prepareExport(survey) }
            text(summary, "Export contains original phone captures and operator observations, and may include identifiers and location. In Veilbreaker Desktop, open a survey and choose Attach mobile survey to add this file.", 12f)
            button(summary, "Delete survey…") {
                val surveyId = survey.getString("survey_id")
                AlertDialog.Builder(context).setTitle("Delete mobile survey?")
                    .setMessage("Permanently delete this survey, its copied captures, and any unsaved note drafts? The phone's last capture and other surveys are kept.")
                    .setNegativeButton("Cancel", null)
                    .setPositiveButton("Delete") { _, _ ->
                        deletingSurveyId = surveyId
                        if (!runSurveyMutation(surveyId, { runCatching { store.delete(surveyId); runCatching { store.list() }.getOrNull() } }) { result ->
                            deletingSurveyId = null
                            result.fold({ updated ->
                                current = null; noteDrafts.clear(); showMoreActions = false; showAllPoints = false
                                listing = updated ?: listing.copy(surveys = listing.surveys.filterNot { it.id == surveyId })
                                message = "Mobile survey deleted. Other surveys and the last capture were kept."
                            }, { error -> message = error.message ?: "Survey could not be deleted." })
                        }) deletingSurveyId = null
                    }.show()
            }
        }
        val pointCard = card("Captured points")
        if (points.length() == 0) text(pointCard, "No points yet. Capture on the phone, then add the saved capture.")
        if (points.length() > 4) button(pointCard, if (showAllPoints) "Show first 4 points" else "Show all ${points.length()} points") { showAllPoints = !showAllPoints; render() }
        for (i in 0 until (if (showAllPoints) points.length() else minOf(points.length(), 4))) {
            val point = points.getJSONObject(i); val capture = point.getJSONObject("capture")
            val pointPanel = LinearLayout(context).apply {
                orientation = VERTICAL; setPadding(dp(10), dp(8), dp(10), dp(10))
                background = GradientDrawable().apply { setColor(Color.parseColor("#102635")); cornerRadius = dp(8).toFloat(); setStroke(dp(1), Color.parseColor("#264253")) }
                pointCard.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(9) })
            }
            val fixes = GpsSpatialModel.savedFixes(capture); val lastFix = fixes.lastOrNull()
            val location = if (lastFix == null) "No usable GPS fix" else {
                val age = lastFix.ageAtReceiptMs?.let { "${it / 1000}s old at receipt" } ?: "age unavailable"
                val accuracy = String.format(java.util.Locale.US, "%.1f", lastFix.accuracy)
                "Last reported fix: ${lastFix.latitude}, ${lastFix.longitude} · ±$accuracy m · $age · ${lastFix.mockLabel()}\n" +
                    "Location observation received ${lastFix.receivedUtc ?: "not exposed"} · Fix time ${lastFix.fixUtc ?: "not exposed"}"
            }
            text(pointPanel, "POINT ${i + 1}", 12f, true).apply { setTextColor(Color.parseColor("#65d7ea")); letterSpacing = 0.06f }
            text(pointPanel, "${capture.optString("created_utc", "Time unavailable")}\n$location", 13f, true)
            text(pointPanel, MobileSurvey.signalSummary(capture), 12f)
            text(pointPanel, "Capture ${capture.getString("capture_id")} · ${capture.getJSONObject("collection").optString("outcome")} · added ${point.getString("attached_utc")}", 12f)
            val operatorNote = (point.opt("operator_note") as? String)?.takeIf { it.length <= 500 && it.none { ch -> ch.isISOControl() && ch != '\n' } }
            if (!operatorNote.isNullOrBlank()) text(pointPanel, "Operator observation · not a measured value\n$operatorNote", 12f)
            else if (point.has("operator_note") && !point.isNull("operator_note") && operatorNote == null) text(pointPanel, "Operator observation unavailable or invalid; the saved survey is unchanged.", 12f)
            if (capture.getString("capture_id") in noteDrafts) text(pointPanel, "Unsaved operator note draft · open the note to review and save it.", 12f, true)
            if (state == "open") button(pointPanel, if (operatorNote.isNullOrBlank()) "Add note to point ${i+1}…" else "Edit note for point ${i+1}…") {
                editPointNote(survey.getString("survey_id"), capture.getString("capture_id"), operatorNote.orEmpty())
            }
            val pointId = capture.getString("capture_id")
            if (pointId in noteDrafts) button(pointPanel, "Discard unsaved note…") {
                AlertDialog.Builder(context).setTitle("Discard unsaved note?")
                    .setMessage("The saved survey and its existing operator observation will remain unchanged.")
                    .setNegativeButton("Keep draft", null)
                    .setPositiveButton("Discard draft") { _, _ -> noteDrafts.remove(pointId); render() }.show()
            }
        }
    }

    private fun pickArchivedCapture(surveyId: String) {
        if (busy || capturing || !externalEnabled) return
        runJob({ archiveStore.list() }) { saved ->
            if (current?.optString("survey_id") != surveyId || !externalEnabled) {
                message = "Survey or collection state changed. Choose the capture again."
                return@runJob
            }
            val points = current?.optJSONArray("points")
            val present = if (points == null) emptySet() else (0 until points.length()).mapNotNull {
                points.optJSONObject(it)?.optJSONObject("capture")?.optString("capture_id")
            }.toSet()
            val choices = saved.filterNot { it.optString("capture_id") in present }.asReversed()
            if (choices.isEmpty()) {
                message = "No archived captures available to add. Save a copy in Reports, or check whether it is already in this survey."
                return@runJob
            }
            val labels = choices.map { capture ->
                val summary = runCatching { MobileSurvey.signalSummary(capture) }.getOrDefault("Signal summary unavailable")
                "${capture.optString("created_utc", "Time unavailable")} · ${capture.optJSONObject("collection")?.optString("outcome") ?: "unknown"}\n$summary\n${capture.optString("capture_id")}"
            }.toTypedArray()
            AlertDialog.Builder(context).setTitle("Choose an archived capture")
                .setNegativeButton("Cancel", null)
                .setItems(labels) { _, index ->
                    if (current?.optString("survey_id") != surveyId || !externalEnabled) {
                        message = "Survey or collection state changed. Choose the capture again."; render()
                    } else {
                        val id = choices[index].getString("capture_id")
                        runSurveyMutation(surveyId, { archiveStore.addToSurvey(store, surveyId, id) }) { updated ->
                            current = updated; message = "Archived capture added as a separate survey point."
                        }
                    }
                }.show()
        }
    }

    private fun editPointNote(surveyId: String, captureId: String, existing: String) {
        if (busy || capturing) return
        val previousDraft = noteDrafts[captureId]
        val entry = EditText(context).apply {
            hint = "Example: concrete pillar between antenna and test point"
            contentDescription = "Operator observation for survey point"
            setTextColor(Color.WHITE); setHintTextColor(Color.LTGRAY)
            setText(noteDrafts[captureId] ?: existing); minLines = 3
            inputType = android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_FLAG_MULTI_LINE or android.text.InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
            filters = arrayOf(android.text.InputFilter.LengthFilter(500))
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) { }
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { noteDrafts[captureId] = s?.toString().orEmpty() }
                override fun afterTextChanged(s: Editable?) { }
            })
        }
        fun cancelEdit() {
            if (previousDraft == null) noteDrafts.remove(captureId) else noteDrafts[captureId] = previousDraft
            render()
        }
        AlertDialog.Builder(context).setTitle("Operator observation")
            .setMessage("Describe visible conditions. This note is operator-entered, is stored with the survey, and does not change the captured measurement. Clear the text to remove the note.")
            .setView(entry).setNegativeButton("Cancel") { _, _ -> cancelEdit() }
            .setOnCancelListener { cancelEdit() }
            .setPositiveButton("Save") { _, _ ->
                val note = entry.text.toString()
                noteDrafts[captureId] = note
                if (busy || capturing) {
                    message = "The survey is busy; the note remains an unsaved draft."; render()
                } else {
                    val write = pendingWrites.register(surveyId)
                    try {
                        runJob({
                            try { store.update(surveyId) { latest -> MobileSurvey.setPointNote(latest, captureId, note) } }
                            catch (error: Exception) { throw IllegalArgumentException("Could not save the note; its draft remains available to review. ${error.message ?: "Try again."}") }
                            finally { write.close() }
                        }) {
                            noteDrafts.remove(captureId)
                            current = it; message = if (note.isBlank()) "Operator observation removed." else "Operator observation saved with the survey point."
                        }
                    } catch (error: Exception) {
                        write.close()
                        busy = false
                        message = "Could not start saving the note; its draft remains available to review."
                        render()
                    }
                }
            }.show()
    }

    private fun startCaptureAndAdd(surveyId: String) {
        if (capturing || busy || !externalEnabled) return
        capturing = true
        val generation = ++captureGeneration
        message = "Capturing a new survey point…"
        render()
        fun completed(result: Result<JSONObject>) {
            handler.post {
                if (!capturing || generation != captureGeneration || activity.isFinishing || activity.isDestroyed) return@post
                capturing = false
                val capture = result.getOrElse {
                    message = it.message ?: "Capture did not complete. Check phone inputs in Live; the survey is unchanged."
                    render(); return@post
                }
                if (current?.optString("survey_id") != surveyId) {
                    message = "Survey changed before capture finished. The saved phone capture was not added."
                    render(); return@post
                }
                val outcome = capture.optJSONObject("collection")?.optString("outcome")
                runSurveyMutation(surveyId, {
                    try {
                        store.update(surveyId) { latest -> MobileSurvey.addNewCapture(latest, capture, Instant.now().toString()) }
                    } catch (error: Exception) {
                        throw IllegalArgumentException("Survey unchanged; the phone capture remains saved. ${error.message ?: "Could not add point."}")
                    }
                }) { updated ->
                    current = updated
                    message = if (outcome == "partial") "Partial capture added. Review missing data and location before using it." else "New capture added as a survey point."
                }
            }
        }
        try { requestCapture(::completed) } catch (_: Exception) {
            capturing = false; captureGeneration++
            message = "Capture could not start. Configure phone inputs in Live; the survey is unchanged."
            render()
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

    /** Register before starting the worker so a recreated workspace cannot load stale data. */
    private fun <T> runSurveyMutation(surveyId: String, work: () -> T, done: (T) -> Unit): Boolean {
        if (busy) return false
        val write = pendingWrites.register(surveyId)
        try {
            runJob({ try { work() } finally { write.close() } }, done)
            return true
        } catch (_: Exception) {
            write.close(); busy = false
            message = "Could not start the survey operation. Check the survey before retrying."
            render()
            return false
        }
    }

    private fun reloadList() {
        runJob({ pendingWrites.awaitAll(); store.list() }) { result -> listing = result; message = "" }
    }

    private fun prepareExport(survey: JSONObject) {
        prepareExportSnapshot("survey") { MobileSurvey.validate(survey).toString().toByteArray(Charsets.UTF_8) }
    }

    private fun prepareReportExport(report: MobileSurveyReport.Report) {
        prepareExportSnapshot("report") { MobileSurveyReport.html(report).toByteArray(Charsets.UTF_8) }
    }

    private fun prepareExportSnapshot(kind: String, encode: () -> ByteArray) {
        if (!externalEnabled || busy || pendingDocument != null) return
        busy = true; preparingExport = true; exportMessage = "Preparing a private export snapshot…"; render()
        try { Thread {
            val result = runCatching { exportStore.stage(kind, encode()) }
            handler.post {
                if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) {
                    result.getOrNull()?.let { try { exportStore.remove(it) } catch (_: Exception) { } }
                    return@post
                }
                busy = false; preparingExport = false
                result.fold({ ref ->
                    pendingDocument = ref
                    if (externalEnabled) openDocument(ref)
                    else exportMessage = "Stop the active Desktop session or capture, then choose a destination."
                }, { error -> exportMessage = "Could not prepare export: ${error.message ?: "Please try again."}" })
                render()
            }
        }.apply { name = "Veilbreaker prepare survey export"; start() } }
        catch (_: Exception) { busy = false; preparingExport = false; exportMessage = "Could not prepare export. The saved survey is unchanged."; render() }
    }

    private fun openDocument(ref: PendingSurveyExportStore.Reference) {
        if (!externalEnabled || exportOperations.status(ref.token)?.running == true) return
        try {
            @Suppress("DEPRECATION")
            activity.startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = if (ref.kind == "survey") "application/json" else "text/html"
                putExtra(Intent.EXTRA_TITLE, if (ref.kind == "survey") "veilbreaker-mobile-survey.json" else "veilbreaker-mobile-survey-report.html")
            }, if (ref.kind == "survey") EXPORT_REQUEST else REPORT_EXPORT_REQUEST)
            exportMessage = "Choose where to save the ${if (ref.kind == "survey") "mobile survey JSON" else "survey report"}."
        } catch (_: Exception) { exportMessage = "Could not open the document picker. The export snapshot is available to retry." }
    }

    fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?): Boolean {
        if (requestCode != EXPORT_REQUEST && requestCode != REPORT_EXPORT_REQUEST) return false
        val ref = pendingDocument
        if (resultCode != Activity.RESULT_OK || data?.data == null) {
            if (ref != null && exportOperations.status(ref.token)?.running == true) {
                exportMessage = "The previous export is still saving."; monitorPendingExport(); render(); return true
            }
            ref?.let { try { exportStore.remove(it) } catch (_: Exception) { } }
            pendingDocument = null; exportMessage = "Export cancelled; the saved survey is unchanged."; render(); return true
        }
        val expectedKind = if (requestCode == EXPORT_REQUEST) "survey" else "report"
        if (ref == null || ref.kind != expectedKind) {
            exportMessage = "Export could not continue because its snapshot is unavailable. The selected document may be empty; the saved survey is unchanged."
            render(); return true
        }
        val uri = data.data!!
        if (!exportOperations.begin(ref.token)) { monitorPendingExport(); render(); return true }
        exportMessage = "Saving verified export snapshot…"; render()
        try { Thread {
            val outcome = runCatching {
                // Read and verify before opening a destination that may be truncated.
                exportStore.writeVerified(ref) {
                    activity.contentResolver.openOutputStream(uri, "wt")
                        ?: throw IllegalArgumentException("Could not write the selected document.")
                }
            }
            exportOperations.finish(ref.token, outcome.exceptionOrNull()?.message ?: if (outcome.isFailure) "Could not write the document." else null)
            handler.post { monitorPendingExport() }
        }.apply { name = "Veilbreaker survey export"; start() } }
        catch (_: Exception) { exportOperations.finish(ref.token, "Could not start export.") }
        monitorPendingExport()
        return true
    }

    private fun monitorPendingExport() {
        if (activity.isFinishing || activity.isDestroyed) return
        val ref = pendingDocument ?: return
        val state = exportOperations.status(ref.token) ?: return
        if (state.running) {
            if (exportMonitorToken != ref.token) {
                exportMonitorToken = ref.token
                handler.postDelayed({ exportMonitorToken = null; monitorPendingExport() }, 400)
            }
            return
        }
        if (state.error == null) {
            try { exportStore.remove(ref) } catch (_: Exception) { }
            pendingDocument = null
            exportMessage = if (ref.kind == "survey") "Mobile survey JSON exported. Attach it to an open survey in Veilbreaker Desktop."
                      else "Survey report exported. Original captures remain in the survey JSON."
        } else {
            exportMessage = "Export failed: ${state.error} The saved survey is unchanged; the selected document may be incomplete."
        }
        render()
    }

    companion object {
        const val EXPORT_REQUEST = 72
        const val REPORT_EXPORT_REQUEST = 73
        private val pendingWrites = SurveyPendingWrites()
        private val exportOperations = SurveyExportOperations()
    }
}
