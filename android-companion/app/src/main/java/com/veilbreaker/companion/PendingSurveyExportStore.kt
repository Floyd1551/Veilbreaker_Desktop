package com.veilbreaker.companion

import java.io.File
import java.io.FileInputStream
import java.io.ByteArrayOutputStream
import java.io.OutputStream
import java.nio.file.Files
import java.security.MessageDigest
import java.util.UUID

/** Private, bounded immutable export bytes; only opaque metadata goes into Android saved state. */
class PendingSurveyExportStore(private val directory: File) {
    data class Reference(val token: String, val sha256: String, val kind: String)

    companion object {
        const val MAX_BYTES = 32 * 1024 * 1024
        private const val MAX_FILES = 16
        private const val MAX_AGE_MS = 7L * 24 * 60 * 60 * 1000
        private val tokenPattern = Regex("[a-f0-9]{32}")
        private val hashPattern = Regex("[a-f0-9]{64}")

        fun reference(token: String?, sha256: String?, kind: String?): Reference? {
            if (token == null || sha256 == null || kind == null || !tokenPattern.matches(token) ||
                !hashPattern.matches(sha256) || kind !in setOf("survey", "report")) return null
            return Reference(token, sha256, kind)
        }

        private fun hash(bytes: ByteArray): String = MessageDigest.getInstance("SHA-256")
            .digest(bytes).joinToString("") { "%02x".format(it.toInt() and 0xff) }
    }

    private fun target(reference: Reference): File {
        require(Companion.reference(reference.token, reference.sha256, reference.kind) != null) { "Invalid pending export reference." }
        val path = File(directory, reference.token + ".snapshot")
        require(path.canonicalFile.parentFile == directory.canonicalFile && !Files.isSymbolicLink(path.toPath())) {
            "Pending export storage is unsafe."
        }
        return path
    }

    @Synchronized fun stage(kind: String, bytes: ByteArray): Reference {
        require(kind in setOf("survey", "report") && bytes.isNotEmpty() && bytes.size <= MAX_BYTES) { "Export snapshot exceeds its size limit or is empty." }
        require(!Files.isSymbolicLink(directory.toPath()) && (directory.isDirectory || directory.mkdirs())) { "Cannot create private export storage." }
        val now = System.currentTimeMillis()
        val files = directory.listFiles() ?: throw IllegalArgumentException("Cannot read private export storage.")
        for (file in files) {
            if ((file.name.matches(Regex("[a-f0-9]{32}\\.(snapshot|pending)"))) &&
                !Files.isSymbolicLink(file.toPath()) && now - file.lastModified() > MAX_AGE_MS) file.delete()
        }
        require((directory.listFiles()?.size ?: MAX_FILES) < MAX_FILES) { "Too many pending survey exports; try again after cleanup." }
        val token = UUID.randomUUID().toString().replace("-", "")
        val ref = Reference(token, hash(bytes), kind)
        val dest = target(ref)
        val temp = File(directory, token + ".pending")
        require(temp.createNewFile()) { "Cannot create export snapshot." }
        try {
            temp.outputStream().use { out -> out.write(bytes); out.flush(); out.fd.sync() }
            require(!dest.exists() && temp.renameTo(dest)) { "Cannot save export snapshot." }
        } catch (error: Exception) {
            temp.delete()
            throw error
        }
        return ref
    }

    fun read(reference: Reference): ByteArray {
        val file = target(reference)
        require(file.isFile && file.length() in 1..MAX_BYTES.toLong()) { "Pending export snapshot is missing or too large." }
        val bytes = FileInputStream(file).use { input ->
            val output = ByteArrayOutputStream()
            val buffer = ByteArray(65536)
            while (true) {
                val count = input.read(buffer)
                if (count < 0) break
                require(output.size() + count <= MAX_BYTES) { "Pending export snapshot is too large." }
                output.write(buffer, 0, count)
            }
            output.toByteArray()
        }
        require(hash(bytes) == reference.sha256) { "Pending export snapshot failed integrity validation." }
        return bytes
    }

    /** Verify the entire staged snapshot before opening a potentially truncating destination. */
    fun writeVerified(reference: Reference, destination: () -> OutputStream) {
        val bytes = read(reference)
        destination().use { it.write(bytes) }
    }

    fun remove(reference: Reference) { target(reference).delete() }
}
