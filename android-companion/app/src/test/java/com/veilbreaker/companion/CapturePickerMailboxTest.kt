package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class CapturePickerMailboxTest {
    @Test fun resultWaitsUntilTheRestoredWorkspaceIsReady() {
        val mailbox = CapturePickerMailbox<String>()
        mailbox.offer("selected destination")
        assertNull(mailbox.takeIfReady(false))
        assertEquals("selected destination", mailbox.takeIfReady(true))
        assertNull(mailbox.takeIfReady(true))
    }

    @Test fun duplicateDeliveryDoesNotReplaceTheOriginalResult() {
        val mailbox = CapturePickerMailbox<String>()
        mailbox.offer("first destination")
        mailbox.offer("second destination")
        assertEquals("first destination", mailbox.takeIfReady(true))
    }
}
