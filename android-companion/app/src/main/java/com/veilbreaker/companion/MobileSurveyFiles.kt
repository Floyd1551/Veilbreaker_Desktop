package com.veilbreaker.companion

import java.io.File
import java.nio.file.Files
import java.nio.file.LinkOption

/** File operations confined to one private mobile-survey journal. */
object MobileSurveyFiles {
    private val idPattern = Regex("[a-f0-9-]{36}")

    fun delete(directory: File, id: String) {
        require(idPattern.matches(id)) { "Invalid survey ID." }
        require(directory.isDirectory) { "Survey storage is unavailable." }
        val root = directory.canonicalFile
        val entries = listOf("$id.json", "$id.json.bak", "$id.json.new").map { File(root, it) }
        require(entries.all { it.canonicalFile.parentFile == root && !Files.isSymbolicLink(it.toPath()) }) {
            "Unsafe survey storage path."
        }
        val existing = entries.filter { Files.exists(it.toPath(), LinkOption.NOFOLLOW_LINKS) }
        require(existing.isNotEmpty()) { "Survey is unavailable." }
        require(existing.all { it.isFile }) { "Survey storage contains an invalid entry." }
        for (entry in existing) {
            if (!entry.delete()) throw IllegalStateException("Some survey files could not be removed.")
        }
    }
}
