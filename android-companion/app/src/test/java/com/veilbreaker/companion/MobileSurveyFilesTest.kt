package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files

class MobileSurveyFilesTest {
    private val id = "11111111-2222-3333-4444-555555555555"
    private val other = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    @Test fun deleteRemovesOnlySelectedJournalAndAtomicSidecars() {
        val root = Files.createTempDirectory("mobile-survey-test").toFile()
        try {
            val surveys = root.resolve("mobile-surveys").apply { mkdir() }
            val originalCapture = root.resolve("last-capture.json").apply { writeText("original") }
            val selected = surveys.resolve("$id.json").apply { writeText("selected") }
            val backup = surveys.resolve("$id.json.bak").apply { writeText("backup") }
            val pending = surveys.resolve("$id.json.new").apply { writeText("pending") }
            val untouched = surveys.resolve("$other.json").apply { writeText("other") }
            MobileSurveyFiles.delete(surveys, id)
            assertFalse(selected.exists()); assertFalse(backup.exists()); assertFalse(pending.exists())
            assertEquals("original", originalCapture.readText())
            assertEquals("other", untouched.readText())
        } finally { root.deleteRecursively() }
    }

    @Test fun missingInvalidAndDirectoryEntriesDoNotDeleteOtherData() {
        val root = Files.createTempDirectory("mobile-survey-test").toFile()
        try {
            val surveys = root.resolve("mobile-surveys").apply { mkdir() }
            val selected = surveys.resolve("$id.json").apply { writeText("selected") }
            surveys.resolve("$id.json.bak").mkdir()
            for (invalid in listOf("../last-capture", "", "a".repeat(35))) {
                try { MobileSurveyFiles.delete(surveys, invalid); fail("invalid id") } catch (_: IllegalArgumentException) { }
            }
            try { MobileSurveyFiles.delete(surveys, other); fail("missing") } catch (_: IllegalArgumentException) { }
            try { MobileSurveyFiles.delete(surveys, id); fail("directory sidecar") } catch (_: IllegalArgumentException) { }
            assertEquals("selected", selected.readText())
        } finally { root.deleteRecursively() }
    }
}
