package com.veilbreaker.companion

import java.nio.file.Files
import org.junit.Assert.*
import org.junit.Test

class PendingSurveyExportStoreTest {
    @Test fun snapshotSurvivesRecreationAndRetainsExactBytes() {
        val dir = Files.createTempDirectory("survey-export-test").toFile()
        try {
            val store = PendingSurveyExportStore(dir)
            val bytes = "survey snapshot: α".toByteArray()
            val reference = store.stage("survey", bytes)
            val restored = PendingSurveyExportStore.reference(reference.token, reference.sha256, reference.kind)!!
            assertArrayEquals(bytes, PendingSurveyExportStore(dir).read(restored))
            PendingSurveyExportStore(dir).remove(restored)
            assertThrows(IllegalArgumentException::class.java) { store.read(restored) }
        } finally { dir.deleteRecursively() }
    }

    @Test fun rejectsAlteredMissingUnsafeAndOversizedSnapshots() {
        val dir = Files.createTempDirectory("survey-export-test").toFile()
        try {
            val store = PendingSurveyExportStore(dir)
            val reference = store.stage("report", "original".toByteArray())
            java.io.File(dir, reference.token + ".snapshot").writeText("modified")
            assertThrows(IllegalArgumentException::class.java) { store.read(reference) }
            var opened = false
            assertThrows(IllegalArgumentException::class.java) {
                store.writeVerified(reference) { opened = true; java.io.ByteArrayOutputStream() }
            }
            assertFalse(opened)
            assertNull(PendingSurveyExportStore.reference("../bad", reference.sha256, "report"))
            assertNull(PendingSurveyExportStore.reference(reference.token, "0".repeat(63), "report"))
            assertNull(PendingSurveyExportStore.reference(reference.token, reference.sha256, "other"))
            assertThrows(IllegalArgumentException::class.java) { store.stage("report", byteArrayOf()) }
            assertThrows(IllegalArgumentException::class.java) { store.stage("survey", ByteArray(PendingSurveyExportStore.MAX_BYTES + 1)) }
        } finally { dir.deleteRecursively() }
    }

    @Test fun stageDoesNotDependOnMutableInputAndRemovalIsIdempotent() {
        val dir = Files.createTempDirectory("survey-export-test").toFile()
        try {
            val store = PendingSurveyExportStore(dir)
            val bytes = "original".toByteArray()
            val reference = store.stage("survey", bytes)
            bytes[0] = 'x'.code.toByte()
            assertEquals("original", String(store.read(reference)))
            store.remove(reference)
            store.remove(reference)
        } finally { dir.deleteRecursively() }
    }
}
