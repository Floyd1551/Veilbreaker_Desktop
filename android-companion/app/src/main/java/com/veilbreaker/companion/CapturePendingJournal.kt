package com.veilbreaker.companion

import java.io.File
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.StandardCopyOption

/** Small app-private recovery record; never stores capture bytes or a document URI. */
class CapturePendingJournal(private val directory: File) {
    data class Entry(val reference: PendingSurveyExportStore.Reference, val captureId: String?)
    sealed class State {
        data object Missing : State()
        data object Cleared : State()
        data object Invalid : State()
        data class Pending(val entry: Entry) : State()
    }

    companion object {
        private val lock = Any()
        private const val HEADER = "veilbreaker.capture.pending.v1"
        private const val MAX_METADATA_BYTES = 1024L
    }

    private fun file(): File = File(directory, "pending.meta")

    private fun safe(path: File): Boolean = !Files.isSymbolicLink(path.toPath())

    fun load(): State = synchronized(lock) { loadLocked() }

    private fun loadLocked(): State {
        val path = file()
        if (!safe(directory) || !safe(path)) return State.Invalid
        if (!path.exists()) return State.Missing
        if (!path.isFile || path.length() !in 1..MAX_METADATA_BYTES) return State.Invalid
        return try {
            val lines = path.readText(StandardCharsets.UTF_8).split('\n')
            if (lines.size == 3 && lines[0] == HEADER && lines[1] == "cleared" && lines[2].isEmpty()) return State.Cleared
            if (lines.size != 6 || lines[0] != HEADER || lines[5].isNotEmpty()) return State.Invalid
            val ref = PendingSurveyExportStore.reference(lines[2], lines[3], lines[1]) ?: return State.Invalid
            if (ref.kind !in setOf("capture", "capture_pdf")) return State.Invalid
            val captureId = if (lines[4].isEmpty()) null else CaptureExportIdentity.validated(lines[4]) ?: return State.Invalid
            State.Pending(Entry(ref, captureId))
        } catch (_: Exception) { State.Invalid }
    }

    /** Refuse to replace another pending or unparseable record. */
    fun save(reference: PendingSurveyExportStore.Reference, captureId: String?) = synchronized(lock) {
        val valid = PendingSurveyExportStore.reference(reference.token, reference.sha256, reference.kind)
        require(valid == reference && reference.kind in setOf("capture", "capture_pdf")) { "Invalid capture export reference." }
        require(captureId == null || CaptureExportIdentity.validated(captureId) == captureId) { "Invalid capture export identity." }
        require(loadLocked() in listOf(State.Missing, State.Cleared)) { "A capture export recovery record already exists or is invalid." }
        writeLocked("$HEADER\n${reference.kind}\n${reference.token}\n${reference.sha256}\n${captureId.orEmpty()}\n")
    }

    /** Only a matching pending record can be retired; the tombstone prevents stale state revival. */
    fun clearIfMatches(reference: PendingSurveyExportStore.Reference): Boolean = synchronized(lock) {
        val current = loadLocked()
        if (current !is State.Pending || current.entry.reference != reference) return false
        writeLocked("$HEADER\ncleared\n")
        true
    }

    /** Explicitly discard unreadable metadata without touching capture or snapshot files. */
    fun discardInvalid(): Boolean = synchronized(lock) {
        if (loadLocked() != State.Invalid) return false
        val target = file()
        require(safe(directory) && safe(target) && target.isFile) { "Capture export recovery storage is unsafe." }
        writeLocked("$HEADER\ncleared\n")
        true
    }

    private fun writeLocked(value: String) {
        require(safe(directory) && (directory.isDirectory || directory.mkdirs())) { "Capture export recovery storage is unsafe." }
        val target = file()
        val temp = File(directory, "pending.meta.next")
        require(safe(target) && safe(temp)) { "Capture export recovery storage is unsafe." }
        temp.outputStream().use { output -> output.write(value.toByteArray(StandardCharsets.UTF_8)); output.flush(); output.fd.sync() }
        try {
            Files.move(temp.toPath(), target.toPath(), StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING)
        } catch (error: java.nio.file.AtomicMoveNotSupportedException) {
            throw IllegalArgumentException("Atomic capture export recovery is unavailable.", error)
        }
    }
}
