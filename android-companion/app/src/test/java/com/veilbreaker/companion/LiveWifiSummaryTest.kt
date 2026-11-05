package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class LiveWifiSummaryTest {
    @Test fun unavailableAndPermissionStatesDoNotInventAConnection() {
        assertTrue(LiveWifiSummary.format(false, false, false, true, null, null, null, null).contains("Wi-Fi off"))
        assertTrue(LiveWifiSummary.format(true, false, false, true, null, null, null, null).contains("No Wi-Fi network reported"))
        assertTrue(LiveWifiSummary.format(true, true, true, false, "secret", -70, 5180, 200).contains("permission"))
        assertFalse(LiveWifiSummary.format(true, true, true, false, "secret", -70, 5180, 200).contains("secret"))
    }

    @Test fun connectionShowsOnlyExposedValuesAndExplicitAgeCaveat() {
        val summary = LiveWifiSummary.format(true, true, true, true, "\"Field\"", -61, 5180, 433)
        assertTrue(summary.contains("Field")); assertTrue(summary.contains("-61 dBm"))
        assertTrue(summary.contains("36 (derived)")); assertTrue(summary.contains("433 Mbps"))
        assertTrue(summary.contains("sample age not exposed"))
        assertTrue(summary.contains("not measured throughput"))
        val redacted = LiveWifiSummary.format(true, true, false, true, "<unknown ssid>", -127, 0, -1)
        assertTrue(redacted.contains("not exposed")); assertFalse(redacted.contains("-127 dBm"))
    }
}
