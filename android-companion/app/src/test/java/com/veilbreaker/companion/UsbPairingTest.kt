package com.veilbreaker.companion
import org.junit.Assert.*
import org.junit.Test

class UsbPairingTest {
    @Test fun tokenRequiresPhoneConfirmationAndMatchingRequest() {
        var clock = 0L
        val pairing = UsbPairing({clock}, "hidden-token")
        pairing.begin("a".repeat(32), "123456")
        assertNull(pairing.poll("a".repeat(32)))
        assertThrows(IllegalArgumentException::class.java) { pairing.poll("b".repeat(32)) }
        pairing.approve("a".repeat(32))
        assertEquals("hidden-token", pairing.poll("a".repeat(32)))
        assertThrows(IllegalArgumentException::class.java) { pairing.poll("a".repeat(32)) }
    }
    @Test fun expiryAndDenialDoNotReleaseToken() {
        var clock = 0L
        val pairing = UsbPairing({clock}, "hidden-token")
        pairing.begin("a".repeat(32), "123456")
        clock = 60001
        assertThrows(IllegalArgumentException::class.java) { pairing.approve("a".repeat(32)) }
        assertThrows(IllegalArgumentException::class.java) { pairing.poll("a".repeat(32)) }
    }
}
