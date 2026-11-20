package com.veilbreaker.companion

import java.util.Locale

/** Conservative interpretation of the capabilities string reported by Android for a scan result. */
object WifiSecurityCapabilities {
    data class Result(val label: String, val note: String, val raw: String?)

    private const val UNKNOWN = "Unknown"
    private val bracketed = Regex("(?:\\[[A-Za-z0-9_+./-]+\\])+")
    private val groups = Regex("\\[([^\\]]+)\\]")
    private val security = Regex("(WPA|WPA2|RSN)-(PSK|SAE|PSK\\+SAE|SAE\\+PSK|EAP|OWE|EAP_SUITE_B_192)-(TKIP|CCMP|GCMP|GCMP-256|CCMP-256)(?:\\+(?:TKIP|CCMP|GCMP|GCMP-256|CCMP-256))*")
    private val metadata = setOf("ESS", "IBSS", "WPS", "MFPC", "MFPR", "UTF-8", "P2P", "HS20")

    fun interpret(raw: String?): Result {
        // The display layer has historically limited this field to 180 characters; a
        // value at that boundary may already have lost a trailing security mode.
        val shown = raw?.map { if (it.isISOControl()) ' ' else it }?.joinToString("")
            ?.trim()?.takeIf { it.isNotEmpty() }
            ?.let { if (it.length > 180) it.take(180) + "…" else it }
        fun result(label: String) = Result(
            label,
            if (label == UNKNOWN) "Android's advertised capabilities are missing, incomplete, or not recognized."
            else "Based on Android's advertised scan capabilities; the active connection and configuration are not verified.",
            shown,
        )
        if (raw.isNullOrEmpty() || raw.length >= 180 || !bracketed.matches(raw)) return result(UNKNOWN)

        val tokens = groups.findAll(raw).map { it.groupValues[1].uppercase(Locale.ROOT) }.toList()
        val modes = mutableSetOf<String>()
        for (token in tokens) {
            when (token) {
                in metadata -> continue
                "OPEN", "WEP", "OWE_TRANSITION" -> modes.add(token)
                else -> {
                    val match = security.matchEntire(token) ?: return result(UNKNOWN)
                    val protocol = match.groupValues[1]
                    val key = match.groupValues[2]
                    val ciphers = token.substringAfter("$protocol-$key-").split('+')
                    if ((key.contains("SAE") || key == "OWE") && "TKIP" in ciphers) return result(UNKNOWN)
                    val mode = when {
                        protocol == "WPA" && key == "PSK" -> "WPA_PSK"
                        protocol == "WPA2" && key == "EAP" -> "WPA2_EAP"
                        protocol == "RSN" && key == "EAP" -> "RSN_EAP"
                        protocol == "RSN" && key == "EAP_SUITE_B_192" && ciphers == listOf("GCMP-256") && "MFPC" in tokens && "MFPR" in tokens -> "WPA3_EAP_192"
                        protocol in setOf("WPA2", "RSN") && key == "PSK" -> "WPA2_PSK"
                        protocol in setOf("WPA2", "RSN") && key == "SAE" -> "WPA3_SAE"
                        protocol in setOf("WPA2", "RSN") && key in setOf("PSK+SAE", "SAE+PSK") -> "TRANSITION"
                        protocol == "RSN" && key == "OWE" -> "OWE"
                        else -> return result(UNKNOWN)
                    }
                    modes.add(mode)
                }
            }
        }
        val label = when (modes) {
            setOf("OPEN") -> "Open"
            setOf("WEP") -> "WEP"
            setOf("WPA_PSK") -> "WPA-Personal"
            setOf("WPA2_PSK") -> "WPA2-Personal"
            setOf("WPA3_SAE") -> "WPA3-Personal"
            setOf("TRANSITION"), setOf("WPA2_PSK", "WPA3_SAE"),
            setOf("TRANSITION", "WPA2_PSK"), setOf("TRANSITION", "WPA3_SAE"),
            setOf("TRANSITION", "WPA2_PSK", "WPA3_SAE") -> "WPA2/WPA3-Personal transition"
            setOf("WPA2_EAP") -> "WPA2-Enterprise"
            setOf("RSN_EAP") -> "RSN Enterprise"
            setOf("WPA3_EAP_192") -> "WPA3-Enterprise 192-bit"
            setOf("OWE") -> "Enhanced Open (OWE)"
            setOf("OWE_TRANSITION"), setOf("OWE", "OWE_TRANSITION") -> "OWE transition"
            else -> UNKNOWN
        }
        return result(label)
    }
}
