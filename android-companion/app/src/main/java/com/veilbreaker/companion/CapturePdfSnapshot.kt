package com.veilbreaker.companion

import java.io.ByteArrayOutputStream
import java.io.OutputStream

/** Bound the rendered document before it is staged or a destination is opened. */
object CapturePdfSnapshot {
    fun render(limit: Int = PendingSurveyExportStore.MAX_BYTES, write: (OutputStream) -> Unit): ByteArray {
        require(limit in 1..PendingSurveyExportStore.MAX_BYTES) { "Invalid PDF size limit." }
        val buffer = ByteArrayOutputStream()
        val output = object : OutputStream() {
            override fun write(value: Int) {
                require(buffer.size() < limit) { "PDF report exceeds the export size limit." }
                buffer.write(value)
            }
            override fun write(bytes: ByteArray, offset: Int, length: Int) {
                require(offset >= 0 && length >= 0 && offset <= bytes.size - length) { "Invalid PDF output." }
                require(length <= limit - buffer.size()) { "PDF report exceeds the export size limit." }
                buffer.write(bytes, offset, length)
            }
        }
        write(output)
        return validate(buffer.toByteArray())
    }

    private fun validate(bytes: ByteArray): ByteArray {
        require(bytes.size in 6..PendingSurveyExportStore.MAX_BYTES && bytes.copyOfRange(0, 5).contentEquals("%PDF-".toByteArray(Charsets.US_ASCII))) {
            "PDF report generation failed."
        }
        return bytes
    }

    /** Validate the file signature before opening a destination that might truncate. */
    fun writeVerified(bytes: ByteArray, destination: () -> OutputStream) {
        validate(bytes)
        destination().use { it.write(bytes) }
    }
}
