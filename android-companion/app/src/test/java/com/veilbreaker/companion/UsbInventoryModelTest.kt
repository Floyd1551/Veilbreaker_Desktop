package com.veilbreaker.companion

import org.junit.Assert.assertEquals
import org.junit.Test

class UsbInventoryModelTest {
    @Test fun identifiesHackRfAsCandidateOnly() {
        assertEquals("HackRF-family candidate", UsbInventoryModel.kind(0x1d50, 0x6089))
        assertEquals("USB peripheral", UsbInventoryModel.kind(0x1d50, 0x608a))
        assertEquals("USB peripheral", UsbInventoryModel.kind(0, 0))
    }
    @Test fun formatsIdsAsFourDigitHex() {
        assertEquals("000a:00ff", UsbInventoryModel.ids(10, 255))
    }
}
