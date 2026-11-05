package com.veilbreaker.companion

import java.util.Locale

/** USB identifiers describe a candidate device, not functioning capture support. */
object UsbInventoryModel {
    fun kind(vendor: Int, product: Int): String =
        if (vendor == 0x1d50 && product == 0x6089) "HackRF-family candidate" else "USB peripheral"

    fun ids(vendor: Int, product: Int): String = String.format(Locale.US, "%04x:%04x", vendor, product)
}
