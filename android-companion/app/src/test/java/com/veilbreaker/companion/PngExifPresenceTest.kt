package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class PngExifPresenceTest {
    private val signature = byteArrayOf(-119, 80, 78, 71, 13, 10, 26, 10)
    private fun chunk(type: String, payload: ByteArray = byteArrayOf()): ByteArray =
        byteArrayOf(0, 0, 0, payload.size.toByte()) + type.toByteArray(Charsets.US_ASCII) + payload + byteArrayOf(0, 0, 0, 0)

    @Test fun imageWithoutExifIsDistinguishedFromDeclaredExif() {
        assertEquals(false, PngExifPresence.hasExif(signature + chunk("IHDR") + chunk("IEND")))
        assertEquals(true, PngExifPresence.hasExif(signature + chunk("IHDR") + chunk("eXIf") + chunk("IEND")))
    }

    @Test fun matchingBytesInsideImageDataAreNotAnExifChunk() {
        assertEquals(false, PngExifPresence.hasExif(signature + chunk("IDAT", "eXIf".toByteArray()) + chunk("IEND")))
    }

    @Test fun malformedOrNonPngInputIsNotAssumedSafe() {
        assertNull(PngExifPresence.hasExif(byteArrayOf(1, 2, 3)))
        assertNull(PngExifPresence.hasExif(signature + byteArrayOf(127, -1, -1, -1, 101, 88, 73, 102)))
        assertNull(PngExifPresence.hasExif(signature + chunk("IHDR")))
    }
}
