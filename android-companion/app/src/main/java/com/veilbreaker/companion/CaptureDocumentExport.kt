package com.veilbreaker.companion

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import org.json.JSONObject
import java.io.File

/** Retains the selected JSON or rendered field report while the document picker is open. */
class CaptureDocumentExport(
    private val activity: Activity,
    state: Bundle?,
    private val allowed: () -> Boolean,
    private val changed: () -> Unit
) {
    private val handler = Handler(Looper.getMainLooper())
    private val store = PendingSurveyExportStore(File(activity.filesDir, "pending-capture-exports"))
    private var reference = (state?.getString("capture_export_kind") ?: "capture")
        .takeIf { it == "capture" || it == "capture_pdf" }
        ?.let { kind -> PendingSurveyExportStore.reference(
            state?.getString("capture_export_token"), state?.getString("capture_export_sha256"), kind) }
    private var captureId = if (reference == null) null else CaptureExportIdentity.validated(state?.getString("capture_export_id"))
    private var preparing = false
    private var pollingToken: String? = null
    var message = state?.getString("capture_export_message").orEmpty().take(500)
        private set

    init {
        if (state?.getBoolean("capture_export_preparing") == true && reference == null)
            message = "Capture export preparation was interrupted. Choose Export again; the saved capture is unchanged."
    }

    val hasPending: Boolean get() = reference != null
    val busy: Boolean get() = preparing || reference?.let { operations.status(it.token)?.running } == true
    val pendingFormat: String get() = if (reference?.kind == "capture_pdf") "PDF" else "JSON"
    val pendingDescription: String get() = captureId?.let { "Pending capture ID: $it" } ?: "Pending capture ID is unavailable; inspect the source capture."

    fun saveState(out: Bundle) {
        reference?.let { out.putString("capture_export_token", it.token); out.putString("capture_export_sha256", it.sha256); out.putString("capture_export_kind", it.kind) }
        out.putString("capture_export_id", captureId)
        out.putString("capture_export_message", message.take(500))
        out.putBoolean("capture_export_preparing", preparing)
    }

    fun activate() { monitor(); changed() }

    fun startJson(capture: JSONObject) = prepare(capture, null)

    fun startPdf(capture: JSONObject, channelPlan: JSONObject) = prepare(capture, channelPlan)

    private fun prepare(capture: JSONObject, channelPlan: JSONObject?) {
        if (!allowed() || busy || reference != null) return
        val snapshot = try { capture.toString(2) }
            catch (_: Exception) { message = "Could not prepare the capture export. The saved capture is unchanged."; changed(); return }
        val planSnapshot = try { channelPlan?.toString() }
            catch (_: Exception) { message = "Could not prepare the field report. The saved capture is unchanged."; changed(); return }
        val kind = if (channelPlan == null) "capture" else "capture_pdf"
        val format = if (channelPlan == null) "JSON" else "PDF"
        val snapshotId = CaptureExportIdentity.fromSnapshot(snapshot)
        preparing = true; message = "Preparing a private capture $format snapshot…"; changed()
        try { Thread {
            val result = runCatching {
                val bytes = if (planSnapshot == null) snapshot.toByteArray(Charsets.UTF_8)
                    else CapturePdfSnapshot.render { output -> CaptureReportPdf.write(JSONObject(snapshot), JSONObject(planSnapshot), output) }
                store.stage(kind, bytes)
            }
            handler.post {
                if (activity.isFinishing || activity.isDestroyed || activity.isChangingConfigurations) {
                    result.getOrNull()?.let { try { store.remove(it) } catch (_: Exception) { } }
                    return@post
                }
                preparing = false
                result.fold({ ref -> reference = ref; captureId = snapshotId; openPicker() }, {
                    message = "Could not prepare the capture $format export. The saved capture is unchanged."
                })
                changed()
            }
        }.apply { name = "Veilbreaker capture export preparation"; start() } }
        catch (_: Exception) { preparing = false; message = "Could not prepare the capture export. The saved capture is unchanged."; changed() }
    }

    fun openPicker() {
        val ref = reference ?: return
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
        val ref = reference ?: return
        if (operations.status(ref.token)?.running == true) return
        try { store.remove(ref) } catch (_: Exception) { }
        reference = null; captureId = null; message = "Pending export discarded. The saved capture is unchanged."; changed()
    }

    fun onResult(request: Int, result: Int, data: Intent?) {
        val ref = reference
        val expectedKind = if (request == PDF_REQUEST) "capture_pdf" else "capture"
        if (ref != null && ref.kind != expectedKind) {
            message = "The selected destination does not match the pending capture export. The saved capture is unchanged."
            changed(); return
        }
        if (result != Activity.RESULT_OK || data?.data == null) {
            if (ref != null && operations.status(ref.token)?.running == true) { monitor(); return }
            ref?.let { try { store.remove(it) } catch (_: Exception) { } }
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
        if (activity.isFinishing || activity.isDestroyed) return
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
            try { store.remove(ref) } catch (_: Exception) { }
            val format = if (ref.kind == "capture_pdf") "PDF report" else "JSON"
            reference = null; captureId = null; message = "Capture $format exported."
        } else {
            message = "Capture export failed. The saved capture is unchanged; the selected document may be incomplete."
        }
        changed()
    }

    companion object {
        const val JSON_REQUEST = 2
        const val PDF_REQUEST = 3
        private val operations = SurveyExportOperations()
    }
}
