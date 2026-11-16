package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class CapturePdfSnapshotTest {
    @Test fun retainsExactRenderedBytes() {
        val pdf = "%PDF-1.4\nfield report\n%%EOF".toByteArray()
        assertArrayEquals(pdf, CapturePdfSnapshot.render(100) { it.write(pdf) })
    }

    @Test fun rejectsInvalidOrTooLargeOutputBeforeItCanBeStaged() {
        assertThrows(IllegalArgumentException::class.java) { CapturePdfSnapshot.render(100) { it.write("not a pdf".toByteArray()) } }
        assertThrows(IllegalArgumentException::class.java) { CapturePdfSnapshot.render(8) { it.write("%PDF-1234".toByteArray()) } }
        assertThrows(IllegalArgumentException::class.java) { CapturePdfSnapshot.render(5) { repeat(6) { _ -> it.write(0) } } }
        var opened = false
        assertThrows(IllegalArgumentException::class.java) {
            CapturePdfSnapshot.writeVerified("not a pdf".toByteArray()) { opened = true; java.io.ByteArrayOutputStream() }
        }
        assertFalse(opened)
    }
}
