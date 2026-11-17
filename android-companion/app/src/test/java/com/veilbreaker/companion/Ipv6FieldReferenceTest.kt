package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class Ipv6FieldReferenceTest {
    @Test fun routerAdvertisementGuidanceIsSearchableAndSeparatesConfigurationSources() {
        val entry = WirelessReferenceLibrary.search("Networking", "SLAAC DHCPv6").first { it.id == "network-ipv6-configuration" }
        val details = ReferenceReaderModel.expanded(entry).joinToString(" ") { it.second }
        assertTrue(details.contains("router advertisement", ignoreCase = true))
        assertTrue(details.contains("default route", ignoreCase = true))
        assertTrue(details.contains("RFC 9915"))
        assertTrue(details.contains("independently", ignoreCase = true))
        assertTrue(entry.sourceUrl.startsWith("https://www.rfc-editor.org/"))
        val table = ReferenceVisualData.table(entry.id)!!
        assertTrue(table.rows.any { it.first.contains("DHCPv6") })
        assertTrue(table.note.contains("not", ignoreCase = true))
    }

    @Test fun ipv6TranslationGuidanceDoesNotAssumeDns64OrInferLiveState() {
        val entry = WirelessReferenceLibrary.search("Networking", "NAT64 464XLAT").first { it.id == "network-ipv6-translation" }
        val details = ReferenceReaderModel.expanded(entry).joinToString(" ") { it.second }
        assertTrue(details.contains("does not require DNS64"))
        assertTrue(details.contains("IPv4 literal", ignoreCase = true))
        assertTrue(details.contains("interface", ignoreCase = true))
        assertTrue(details.contains("does not prove", ignoreCase = true))
        val table = ReferenceVisualData.table(entry.id)!!
        assertTrue(table.rows.any { it.first.contains("464XLAT") })
        assertTrue(table.note.contains("not measured", ignoreCase = true))
    }
}
