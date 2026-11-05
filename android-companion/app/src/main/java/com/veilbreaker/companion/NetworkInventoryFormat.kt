package com.veilbreaker.companion

/** Presentation of Android-reported connection state; no network measurements are inferred. */
object NetworkInventoryFormat {
    data class Snapshot(
        val active: Boolean? = null,
        val transports: List<String> = emptyList(),
        val internet: Boolean? = null,
        val validated: Boolean? = null,
        val captivePortal: Boolean? = null,
        val metered: Boolean? = null,
        val interfaceName: String? = null,
        val addresses: List<String> = emptyList(),
        val dns: List<String> = emptyList(),
        val routes: List<String> = emptyList(),
        val mtu: Int? = null,
        val privateDns: String? = null
    )

    fun describe(value: Snapshot): String {
        fun entries(label: String, values: List<String>): String = "$label: " +
            values.filter { it.isNotBlank() }.joinToString(", ").ifEmpty { "not exposed" }
        fun yesNo(value: Boolean?): String = when (value) { true -> "yes"; false -> "no"; null -> "not exposed" }
        val transports = value.transports.joinToString(" + ").ifBlank { "Transport not exposed" }
        val validation = when (value.validated) { true -> "reported validated"; false -> "not reported validated"; null -> "not exposed" }
        return listOf(
            transports + when (value.active) { true -> " · default network"; false -> " · non-default network"; null -> " · default status not exposed" },
            "Internet capability: ${yesNo(value.internet)} · Validation: $validation",
            "Captive portal indicated: ${yesNo(value.captivePortal)} · Metered: ${yesNo(value.metered)}",
            "Interface: ${value.interfaceName?.takeIf { it.isNotBlank() } ?: "not exposed"}",
            entries("IP addresses", value.addresses),
            entries("DNS servers", value.dns),
            "Private DNS: ${value.privateDns ?: "not exposed"}",
            entries("Routes", value.routes),
            "MTU: ${value.mtu?.takeIf { it > 0 }?.toString() ?: "default or not exposed"}"
        ).joinToString("\n")
    }
}
