package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class WifiSnapshotFormatTest {
    @Test fun channelRecognizesCenterFrequenciesOnly() {
        assertEquals(1, WifiSnapshotFormat.channel(2412))
        assertEquals(14, WifiSnapshotFormat.channel(2484))
        assertEquals(36, WifiSnapshotFormat.channel(5180))
        assertEquals(2, WifiSnapshotFormat.channel(5935))
        assertEquals(1, WifiSnapshotFormat.channel(5955))
        assertEquals(233, WifiSnapshotFormat.channel(7115))
        assertNull(WifiSnapshotFormat.channel(2413))
        assertNull(WifiSnapshotFormat.channel(0))
    }
    @Test fun redactedIdentityRemainsUnknown() {
        assertNull(WifiSnapshotFormat.ssid("<unknown ssid>"))
        assertNull(WifiSnapshotFormat.ssid("\"<unknown ssid>\""))
        assertNull(WifiSnapshotFormat.ssid(""))
        assertEquals("Field Wi-Fi", WifiSnapshotFormat.ssid("\"Field Wi-Fi\""))
        assertEquals("A B", WifiSnapshotFormat.ssid("\"A\nB\""))
        assertNull(WifiSnapshotFormat.bssid("02:00:00:00:00:00"))
        assertNull(WifiSnapshotFormat.bssid("invalid"))
        assertEquals("aa:bb:cc:dd:ee:ff", WifiSnapshotFormat.bssid("AA:BB:CC:DD:EE:FF"))
    }
    @Test fun freshnessUsesMonotonicReceiptTimeAndRejectsInvalidClocks() {
        assertEquals(3L, WifiSnapshotFormat.ageSeconds(12_000L, 9_000_000L))
        assertNull(WifiSnapshotFormat.ageSeconds(12_000L, 0L))
        assertNull(WifiSnapshotFormat.ageSeconds(12_000L, 13_000_000L))
        assertNull(WifiSnapshotFormat.ageSeconds(12_000L, 12_000_001L))
    }
    @Test fun unavailableSelectedNetworkDoesNotBorrowLegacyAssociation() {
        var consulted = false
        assertNull(WifiSnapshotFormat.association<String>(true, null) { consulted = true; "other network" })
        assertFalse(consulted)
        assertEquals("selected", WifiSnapshotFormat.association(true, "selected") { "other network" })
        assertEquals("legacy", WifiSnapshotFormat.association(false, null) { "legacy" })
    }
}
