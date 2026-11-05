package com.veilbreaker.companion

/** Inspect PNG chunks, not image pixels; null means malformed or not a PNG. */
object PngExifPresence {
    private val signature = byteArrayOf(-119, 80, 78, 71, 13, 10, 26, 10)

    fun hasExif(bytes: ByteArray): Boolean? {
        if (bytes.size < signature.size || !bytes.copyOfRange(0, signature.size).contentEquals(signature)) return null
        var pos = signature.size
        var found = false
        while (pos <= bytes.size - 12) {
            val length = ((bytes[pos].toLong() and 0xff) shl 24) or
                ((bytes[pos + 1].toLong() and 0xff) shl 16) or
                ((bytes[pos + 2].toLong() and 0xff) shl 8) or (bytes[pos + 3].toLong() and 0xff)
            if (length > bytes.size.toLong() - pos - 12) return null
            val type = String(bytes, pos + 4, 4, Charsets.US_ASCII)
            if (type == "eXIf") found = true
            if (type == "IEND") return found
            pos += (length + 12).toInt()
        }
        return null
    }
}
