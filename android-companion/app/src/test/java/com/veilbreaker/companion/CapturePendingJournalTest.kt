package com.veilbreaker.companion

import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class CapturePendingJournalTest {
    @Test fun recoversValidPendingMetadataWithoutCaptureOrDestinationData() {
        val dir = Files.createTempDirectory("pending-capture-journal").toFile()
        try {
            val store = PendingSurveyExportStore(dir.resolve("snapshots"))
            val payload = "private capture bytes".toByteArray()
            val ref = store.stage("capture", payload)
            val id = "c41af3b7-97ce-43a2-8d66-b4c8009b02ce"
            val journal = CapturePendingJournal(dir.resolve("journal"))
            journal.save(ref, id)
            val restored = (CapturePendingJournal(dir.resolve("journal")).load() as CapturePendingJournal.State.Pending).entry
            assertEquals(ref, restored.reference)
            assertEquals(id, restored.captureId)
            assertArrayEquals(payload, store.read(restored.reference))
            assertFalse(dir.resolve("journal/pending.meta").readText().contains("private capture"))
        } finally { dir.deleteRecursively() }
    }

    @Test fun staleCleanupCannotClearANewerPendingReference() {
        val dir = Files.createTempDirectory("pending-capture-journal").toFile()
        try {
            val store = PendingSurveyExportStore(dir.resolve("snapshots"))
            val one = store.stage("capture", "first".toByteArray())
            val two = store.stage("capture_pdf", "%PDF-second".toByteArray())
            val journal = CapturePendingJournal(dir.resolve("journal"))
            journal.save(one, null)
            assertTrue(journal.clearIfMatches(one))
            journal.save(two, null)
            assertFalse(journal.clearIfMatches(one))
            assertEquals(two, (journal.load() as CapturePendingJournal.State.Pending).entry.reference)
            assertTrue(journal.clearIfMatches(two))
            assertEquals(CapturePendingJournal.State.Cleared, journal.load())
        } finally { dir.deleteRecursively() }
    }

    @Test fun aSecondPendingExportCannotOverwriteTheFirst() {
        val dir = Files.createTempDirectory("pending-capture-journal").toFile()
        try {
            val store = PendingSurveyExportStore(dir.resolve("snapshots"))
            val one = store.stage("capture", "first".toByteArray())
            val two = store.stage("capture", "second".toByteArray())
            val journal = CapturePendingJournal(dir.resolve("journal"))
            journal.save(one, null)
            assertThrows(IllegalArgumentException::class.java) { journal.save(two, null) }
            assertEquals(one, (journal.load() as CapturePendingJournal.State.Pending).entry.reference)
        } finally { dir.deleteRecursively() }
    }

    @Test fun corruptMetadataIsPreservedAndNeverInventsAnExport() {
        val dir = Files.createTempDirectory("pending-capture-journal").toFile()
        try {
            val journal = CapturePendingJournal(dir)
            val corrupt = dir.resolve("pending.meta")
            corrupt.writeText("invalid metadata")
            assertEquals(CapturePendingJournal.State.Invalid, journal.load())
            assertFalse(journal.clearIfMatches(PendingSurveyExportStore.Reference("0".repeat(32), "0".repeat(64), "capture")))
            assertEquals("invalid metadata", corrupt.readText())
            assertTrue(journal.discardInvalid())
            assertEquals(CapturePendingJournal.State.Cleared, journal.load())
        } finally { dir.deleteRecursively() }
    }

    @Test fun missingAndClearedJournalAreDistinguishedFromOrphanSnapshots() {
        val dir = Files.createTempDirectory("pending-capture-journal").toFile()
        try {
            val journal = CapturePendingJournal(dir.resolve("journal"))
            val store = PendingSurveyExportStore(dir.resolve("snapshots"))
            val orphan = store.stage("capture", "saved copy".toByteArray())
            assertEquals(CapturePendingJournal.State.Missing, journal.load())
            journal.save(orphan, null)
            assertTrue(journal.clearIfMatches(orphan))
            assertEquals(CapturePendingJournal.State.Cleared, journal.load())
            assertArrayEquals("saved copy".toByteArray(), store.read(orphan))
        } finally { dir.deleteRecursively() }
    }

    @Test fun alteredSnapshotRemainsPendingButCannotBeExported() {
        val dir = Files.createTempDirectory("pending-capture-journal").toFile()
        try {
            val store = PendingSurveyExportStore(dir.resolve("snapshots"))
            val ref = store.stage("capture", "original".toByteArray())
            val journal = CapturePendingJournal(dir.resolve("journal"))
            journal.save(ref, null)
            dir.resolve("snapshots/${ref.token}.snapshot").writeText("altered")
            val pending = (journal.load() as CapturePendingJournal.State.Pending).entry.reference
            var opened = false
            assertThrows(IllegalArgumentException::class.java) {
                store.writeVerified(pending) { opened = true; java.io.ByteArrayOutputStream() }
            }
            assertFalse(opened)
            assertEquals(ref, (journal.load() as CapturePendingJournal.State.Pending).entry.reference)
        } finally { dir.deleteRecursively() }
    }
}
