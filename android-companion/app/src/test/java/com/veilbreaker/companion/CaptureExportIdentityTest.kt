package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class CaptureExportIdentityTest {
    @Test fun identifiesOnlyCanonicalUuidFromEncodedSnapshot() {
        val id = "57dd5784-d103-4f66-9c68-9fbb173a8120"
        assertEquals(id, CaptureExportIdentity.fromSnapshot("{\"capture_id\":\"$id\"}"))
        assertNull(CaptureExportIdentity.fromSnapshot("{\"capture_id\":\"../other.json\"}"))
        assertNull(CaptureExportIdentity.fromSnapshot("{\"capture_id\":\"1-2-3-4-5\"}"))
        assertNull(CaptureExportIdentity.fromSnapshot("{}"))
        assertNull(CaptureExportIdentity.fromSnapshot("invalid"))
    }

    @Test fun invalidRestoredIdentityCannotBecomeFilename() {
        assertNull(CaptureExportIdentity.validated("../unsafe"))
        assertNull(CaptureExportIdentity.validated(null))
        val id = "57dd5784-d103-4f66-9c68-9fbb173a8120"
        assertEquals(id, CaptureExportIdentity.validated(id))
    }
}
