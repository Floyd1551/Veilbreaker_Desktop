package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class SurveyExportOperationsTest {
    @Test fun recreatedWorkspaceCanObserveAndCannotDuplicateAnInFlightWrite() {
        val ops = SurveyExportOperations()
        assertTrue(ops.begin("token"))
        assertFalse(ops.begin("token"))
        assertTrue(ops.status("token")!!.running)
        ops.finish("token", null)
        assertFalse(ops.status("token")!!.running)
        assertNull(ops.status("token")!!.error)
        assertFalse(ops.begin("token"))
        assertNull(ops.status("other"))
    }

    @Test fun failedWriteCanBeRetriedWithSameSnapshot() {
        val ops = SurveyExportOperations()
        assertTrue(ops.begin("token"))
        ops.finish("token", "write failed")
        assertEquals("write failed", ops.status("token")!!.error)
        assertTrue(ops.begin("token"))
        assertTrue(ops.status("token")!!.running)
    }
}
