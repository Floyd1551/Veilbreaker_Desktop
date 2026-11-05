package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class NetworkInventoryFormatTest {
    @Test fun missingDataIsExplicitAndNeverInventsInternetOrMtu() {
        val row = NetworkInventoryFormat.describe(NetworkInventoryFormat.Snapshot())
        assertTrue(row.contains("Internet capability: not exposed"))
        assertTrue(row.contains("Validation: not exposed"))
        assertTrue(row.contains("MTU: default or not exposed"))
        assertTrue(row.contains("IP addresses: not exposed"))
        assertFalse(row.contains("1500"))
    }

    @Test fun showsSelectedNetworkPropertiesWithoutTreatingValidationAsSpeed() {
        val row = NetworkInventoryFormat.describe(NetworkInventoryFormat.Snapshot(
            active = true, transports = listOf("Ethernet"), internet = true,
            validated = false, captivePortal = false, metered = false,
            interfaceName = "eth0", addresses = listOf("192.0.2.4/24"),
            dns = listOf("192.0.2.53"), routes = listOf("0.0.0.0/0 via 192.0.2.1"), mtu = 1400))
        assertTrue(row.contains("Ethernet · default network"))
        assertTrue(row.contains("Validation: not reported validated"))
        assertTrue(row.contains("192.0.2.4/24"))
        assertTrue(row.contains("192.0.2.53"))
        assertTrue(row.contains("0.0.0.0/0 via 192.0.2.1"))
        assertTrue(row.contains("MTU: 1400"))
        assertFalse(row.contains("Mbps"))
    }

    @Test fun ipv6AndDefaultRouteRemainDistinct() {
        val row = NetworkInventoryFormat.describe(NetworkInventoryFormat.Snapshot(
            active = null, transports = listOf("VPN"), addresses = listOf("2001:db8::1/64"),
            routes = listOf("::/0 via fe80::1")))
        assertTrue(row.contains("default status not exposed"))
        assertTrue(row.contains("2001:db8::1/64"))
        assertTrue(row.contains("::/0 via fe80::1"))
    }
}
