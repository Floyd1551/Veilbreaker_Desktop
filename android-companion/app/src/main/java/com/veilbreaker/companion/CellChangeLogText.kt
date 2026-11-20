package com.veilbreaker.companion

/** Text for transient observations, with role and receipt-time provenance. */
object CellChangeLogText {
    fun event(event: ServingCellChangeTracker.Event): String {
        fun identity(value: ServingCellChangeTracker.Identity, role: String): String {
            val roleLabel = if (role == "primary") "primary serving" else "registered; role unconfirmed"
            val channelLabel = if (value.radio == "LTE") "EARFCN" else "NR-ARFCN"
            return "${value.radio} ${value.mcc}/${value.mnc} · cell ${value.cellId} · PCI ${value.pci} · $channelLabel ${value.channel} · $roleLabel"
        }
        return "Reported change · response received ${event.receivedUtc ?: "time unavailable"} (UTC)\n" +
            "From: ${identity(event.previous, event.previousRole)}\nTo: ${identity(event.current, event.currentRole)}\n" +
            "${event.source} · modem age at receipt ${event.ageAtReceiptMs} ms"
    }
}
