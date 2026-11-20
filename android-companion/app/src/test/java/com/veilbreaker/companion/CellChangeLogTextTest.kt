package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class CellChangeLogTextTest {
    @Test fun formatsReceiptIdentityRoleAndAgeWithoutClaimingTower() {
        val previous = ServingCellChangeTracker.Identity("LTE", "311", "480", "123", 17, 5230)
        val current = ServingCellChangeTracker.Identity("NR", "311", "480", "456", 25, 640000)
        val event = ServingCellChangeTracker.Event(previous, current, 10000, "2026-11-20T12:00:00Z", 9000, 1000,
            previousRole = "primary", currentRole = "registered_role_unconfirmed")
        val text = CellChangeLogText.event(event)
        assertTrue(text.contains("response received 2026-11-20T12:00:00Z"))
        assertTrue(text.contains("LTE 311/480")); assertTrue(text.contains("EARFCN 5230"))
        assertTrue(text.contains("NR-ARFCN 640000")); assertTrue(text.contains("role unconfirmed"))
        assertTrue(text.contains("age at receipt 1000 ms"))
        assertFalse(text.contains("tower", ignoreCase = true))
    }
}
