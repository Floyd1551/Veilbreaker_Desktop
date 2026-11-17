package com.veilbreaker.companion

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.io.File
import java.lang.ref.WeakReference

/** Retains the selected JSON or rendered field report while the document picker is open. */
class CaptureDocumentExport(
    private val activity: Activity,
    state: Bundle?,
    private val allowed: () -> Boolean,
    private val changed: () -> Unit
) {
    private val handler = Handler(Looper.getMainLooper())
    private val store = PendingSurveyExportStore(File(activity.filesDir, "pending-capture-exports"))
    private val journal = CapturePendingJournal(File(activity.filesDir, "capture-export-recovery"))
    private val legacyReference = (state?.getString("capture_export_kind") ?: "capture")
        .takeIf { it == "capture" || it == "capture_pdf" }
        ?.let { kind -> PendingSurveyExportStore.reference(
            state?.getString("capture_export_token"), state?.getString("capture_export_sha256"), kind) }
    private val legacyCaptureId = CaptureExportIdentity.validated(state?.getString("capture_export_id"))
    private var reference: PendingSurveyExportStore.Reference? = null
    private var captureId: String? = null
    private var recovering = true
    private var invalidRecord = false
    private var invalidSnapshot = false
    private var preparing = false
    private var retiring = false
    private var pollingToken: String? = null
    var message = state?.getString("capture_export_message").orEmpty().take(500)
        private set

    init {
        if (state?.getBoolean("capture_export_preparing") == true)
            message = "Capture export preparation was interrupted. Choose Export again; the saved capture is unchanged."
    }

    val hasPending: Boolean get() = reference != null || invalidRecord
    val busy: Boolean get() = recovering || preparing || retiring || reference?.let { operations.status(it.token)?.running } == true
    val canRetry: Boolean get() = !recovering && (invalidRecord || (reference != null && !invalidSnapshot))
    val retryText: String get() = if (invalidRecord) "Check pending export again" else "Choose $pendingFormat export destination…"
    val pendingFormat: String get() = if (reference?.kind == "capture_pdf") "PDF" else "JSON"
    val pendingDescription: String get() = when {
        invalidRecord -> "The pending export record is invalid. Discard the record to continue; saved captures are unchanged."
        invalidSnapshot -> "The pending snapshot is unavailable or failed verification. Discard it and export the source capture again."
        else -> captureId?.let { "Pending capture ID: $it" } ?: "Pending capture ID is unavailable; inspect the source capture."
    }

    fun saveState(out: Bundle) {
        val pending = reference ?: if (recovering) legacyReference else null
        pending?.let { out.putString("capture_export_token", it.token); out.putString("capture_export_sha256", it.sha256); out.putString("capture_export_kind", it.kind) }
        out.putString("capture_export_id", captureId ?: if (recovering) legacyCaptureId else null)
        out.putString("capture_export_message", message.take(500))
        out.putBoolean("capture_export_preparing", preparing)
    }

    fun activate() {
        if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) return
        synchronized(queuedLock) { activeWorkspace = WeakReference(this) }
        // Journal lookup and verification can involve a large staged file. Never block the UI.
        recovering = true; changed()
        try { Thread {
            val recovery = runCatching {
                preparations.awaitAll()
                retirements.awaitAll()
                var state = journal.load()
                if (state == CapturePendingJournal.State.Missing && legacyReference != null) {
                    journal.save(legacyReference, legacyCaptureId)
                    state = journal.load()
                }
                val entry = (state as? CapturePendingJournal.State.Pending)?.entry
                val badSnapshot = entry != null && runCatching { store.read(entry.reference) }.isFailure
                Triple(state, entry, badSnapshot)
            }
            handler.post {
                if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) return@post
                recovering = false
                recovery.fold({ (state, entry, badSnapshot) ->
                    invalidRecord = state == CapturePendingJournal.State.Invalid
                    reference = entry?.reference; captureId = entry?.captureId; invalidSnapshot = badSnapshot
                    if (invalidRecord) message = "Pending capture export metadata is invalid; saved captures were not changed."
                    else if (badSnapshot) message = "Pending capture export could not be verified; saved captures were not changed."
                    else if (entry != null && operations.status(entry.reference.token) == null)
                        message = "A capture export was recovered. If a previous save was interrupted, check the destination before retrying."
                    else if (state == CapturePendingJournal.State.Cleared && legacyReference != null)
                        message = "Previous export cleanup finished. Check the destination if saving was interrupted."
                }, { invalidRecord = true; message = "Could not check pending capture exports; saved captures were not changed." })
                if (!drainQueuedResult()) { monitor(); changed() }
            }
        }.apply { name = "Veilbreaker capture export recovery"; start() } }
        catch (_: Exception) { recovering = false; invalidRecord = true; message = "Could not check pending capture exports; saved captures were not changed."; changed() }
    }

    fun startJson(capture: JSONObject) = prepare(capture, null)

    fun startPdf(capture: JSONObject, channelPlan: JSONObject) = prepare(capture, channelPlan)

    private fun prepare(capture: JSONObject, channelPlan: JSONObject?) {
        if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) return
        if (!allowed() || busy || hasPending) return
        val snapshot = try { capture.toString(2) }
            catch (_: Exception) { message = "Could not prepare the capture export. The saved capture is unchanged."; changed(); return }
        val planSnapshot = try { channelPlan?.toString() }
            catch (_: Exception) { message = "Could not prepare the field report. The saved capture is unchanged."; changed(); return }
        val kind = if (channelPlan == null) "capture" else "capture_pdf"
        val format = if (channelPlan == null) "JSON" else "PDF"
        val snapshotId = CaptureExportIdentity.fromSnapshot(snapshot)
        preparing = true; message = "Preparing a private capture $format snapshot…"; changed()
        val preparation = preparations.register("capture")
        try { Thread {
            val result = try { runCatching {
                val bytes = if (planSnapshot == null) snapshot.toByteArray(Charsets.UTF_8)
                    else CapturePdfSnapshot.render { output -> CaptureReportPdf.write(JSONObject(snapshot), JSONObject(planSnapshot), output) }
                val ref = store.stage(kind, bytes)
                journal.save(ref, snapshotId)
                ref
            } } finally { preparation.close() }
            handler.post {
                if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) {
                    return@post
                }
                preparing = false
                result.fold({ ref -> reference = ref; captureId = snapshotId; openPicker() }, {
                    message = "Could not prepare the capture $format export. The saved capture is unchanged."
                    activate()
                })
                changed()
            }
        }.apply { name = "Veilbreaker capture export preparation"; start() } }
        catch (_: Exception) { preparation.close(); preparing = false; message = "Could not prepare the capture export. The saved capture is unchanged."; changed() }
    }

    fun openPicker() {
        if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) return
        if (invalidRecord && !recovering) { activate(); return }
        val ref = reference ?: return
        if (recovering || invalidSnapshot) return
        if (operations.status(ref.token)?.running == true) return
        if (!allowed()) { message = "Stop the active Desktop session or capture, then choose a destination."; changed(); return }
        try {
            @Suppress("DEPRECATION")
            activity.startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                addCategory(Intent.CATEGORY_OPENABLE)
                type = if (ref.kind == "capture_pdf") "application/pdf" else "application/json"
                putExtra(Intent.EXTRA_TITLE, "veilbreaker-" + (captureId ?: "capture") + (if (ref.kind == "capture_pdf") "-field-report.pdf" else ".json"))
            }, if (ref.kind == "capture_pdf") PDF_REQUEST else JSON_REQUEST)
            message = "Choose where to save the capture $pendingFormat."
        } catch (_: Exception) { message = "Could not open the document picker. The export snapshot is available to retry." }
        changed()
    }

    fun discard() {
        if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) return
        if (recovering || retiring) return
        if (invalidRecord) {
            retireAsync(null, "Invalid export record discarded. Saved captures are unchanged.",
                "Could not discard the invalid export record. Saved captures are unchanged.")
            return
        }
        val ref = reference ?: return
        if (operations.status(ref.token)?.running == true) return
        retireAsync(ref, "Pending export discarded. The saved capture is unchanged.",
            "Could not discard the pending export. Saved captures are unchanged.")
    }

    fun onResult(request: Int, result: Int, data: Intent?) {
        if (activity.isFinishing || activity.isDestroyed) return
        if (recovering || activity.isChangingConfigurations) {
            queuedResult.offer(PickerResult(request, result, data))
            val target = synchronized(queuedLock) { activeWorkspace?.get() }
            target?.handler?.post { target.drainQueuedResult() }
            message = "Checking the pending export before saving…"; changed(); return
        }
        if (retiring) { message = "Finishing the pending export…"; changed(); return }
        val ref = reference
        val expectedKind = if (request == PDF_REQUEST) "capture_pdf" else "capture"
        if (ref != null && ref.kind != expectedKind) {
            message = "The selected destination does not match the pending capture export. The saved capture is unchanged."
            changed(); return
        }
        if (result != Activity.RESULT_OK || data?.data == null) {
            if (ref != null && operations.status(ref.token)?.running == true) { monitor(); return }
            if (ref != null) {
                retireAsync(ref, "Capture export cancelled; the saved capture is unchanged.",
                    "Could not clear the pending export. Saved captures are unchanged.")
                return
            }
            reference = null; captureId = null; message = "Capture export cancelled; the saved capture is unchanged."; changed(); return
        }
        if (ref == null) {
            message = "The export snapshot is unavailable. The selected document may be empty; the saved capture is unchanged."
            changed(); return
        }
        val uri = data.data!!
        if (!operations.begin(ref.token)) { monitor(); changed(); return }
        message = "Saving verified capture export…"; changed()
        val resolver = activity.applicationContext.contentResolver
        try { Thread {
            val outcome = runCatching {
                val bytes = store.read(ref)
                val destination = { resolver.openOutputStream(uri, "wt") ?: error("Could not write the selected document.") }
                if (ref.kind == "capture_pdf") CapturePdfSnapshot.writeVerified(bytes, destination)
                else destination().use { it.write(bytes) }
            }
            operations.finish(ref.token, outcome.exceptionOrNull()?.message ?: if (outcome.isFailure) "Could not write the document." else null)
            handler.post { monitor() }
        }.apply { name = "Veilbreaker capture export"; start() } }
        catch (_: Exception) { operations.finish(ref.token, "Could not start export.") }
        monitor()
    }

    private fun monitor() {
        if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations || retiring) return
        val ref = reference ?: return
        val result = operations.status(ref.token)
        if (result == null) {
            if (message.isBlank() || message.startsWith("Saving"))
                message = "A capture export is pending. If a previous save was interrupted, check the destination before retrying."
            changed(); return
        }
        if (result.running) {
            if (pollingToken != ref.token) {
                pollingToken = ref.token
                handler.postDelayed({ pollingToken = null; monitor() }, 400)
            }
            changed(); return
        }
        if (result.error == null) {
            val format = if (ref.kind == "capture_pdf") "PDF report" else "JSON"
            retireAsync(ref, "Capture $format exported.",
                "The export may have completed, but recovery state could not be cleared. Check the destination before retrying.")
            return
        } else {
            message = "Capture export failed. The saved capture is unchanged; the selected document may be incomplete."
        }
        changed()
    }

    /** A second live workspace may already have retired the same completed export. */
    private fun retire(ref: PendingSurveyExportStore.Reference): Boolean =
        journal.clearIfMatches(ref) || journal.load() == CapturePendingJournal.State.Cleared

    private fun drainQueuedResult(): Boolean {
        val ready = !recovering && !retiring && !activity.isFinishing && !activity.isDestroyed && !activity.isChangingConfigurations
        val queued = queuedResult.takeIfReady(ready) ?: return false
        onResult(queued.request, queued.result, queued.data)
        return true
    }

    /** Retire journal metadata and remove only the matching staged copy off the UI thread. */
    private fun retireAsync(ref: PendingSurveyExportStore.Reference?, success: String, failure: String) {
        if (retiring) return
        val ticket = retirements.register("capture")
        retiring = true; message = "Finishing the pending export…"; changed()
        try {
            Thread {
                val result = try { runCatching {
                    if (ref == null) require(journal.discardInvalid())
                    else {
                        require(retire(ref)) { "The pending export changed." }
                        try { store.remove(ref) } catch (_: Exception) { }
                    }
                } } finally { ticket.close() }
                handler.post {
                    if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) return@post
                    retiring = false
                    result.fold({
                        if (ref == null) invalidRecord = false
                        else if (reference == ref) { reference = null; captureId = null; invalidSnapshot = false }
                        message = success
                    }, { message = failure })
                    changed()
                    drainQueuedResult()
                }
            }.apply { name = "Veilbreaker capture export cleanup"; start() }
        } catch (_: Exception) {
            ticket.close(); retiring = false; message = failure; changed()
        }
    }

    companion object {
        const val JSON_REQUEST = 2
        const val PDF_REQUEST = 3
        private val operations = SurveyExportOperations()
        private val preparations = SurveyPendingWrites()
        private val retirements = SurveyPendingWrites()
        private data class PickerResult(val request: Int, val result: Int, val data: Intent?)
        private val queuedLock = Any()
        private val queuedResult = CapturePickerMailbox<PickerResult>()
        private var activeWorkspace: WeakReference<CaptureDocumentExport>? = null
    }
}
