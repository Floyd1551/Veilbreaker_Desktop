package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class NetworkReferenceDetailsTest {
    @Test fun everyNetworkingAndFiberEntryHasSpecificOfflineNotesAndSources() {
        val entries = WirelessReferenceLibrary.entries.filter { it.category in setOf("Networking", "Fiber & Power") }
        assertTrue(entries.isNotEmpty())
        for (entry in entries) {
            val body = NetworkReferenceDetails.details(entry.id)
            assertNotNull("Missing details for ${entry.id}", body)
            assertTrue("Field detail missing for ${entry.id}", body!!.contains("FIELD METHOD"))
            assertTrue("Provenance missing for ${entry.id}", body.contains("https://"))
        }
        assertNull(NetworkReferenceDetails.details("not-a-reference"))
    }
}
