package com.veilbreaker.companion

import java.util.Locale

/** Pure selection and ordering of already cached Android observations. */
object WifiObservationFilter {
    enum class Band { ALL, GHZ_24, GHZ_5, GHZ_6 }
    enum class Order { SIGNAL, FREQUENCY, AGE }
    data class Row(val ssid: String?, val bssid: String?, val frequencyMhz: Int, val rssiDbm: Int, val ageSeconds: Long?,
                   val reportedWidth: Int? = null, val center0Mhz: Int? = null, val center1Mhz: Int? = null,
                   val securityCapabilities: String? = null)
    fun select(rows: List<Row>, query: String, band: Band, order: Order): List<Row> {
        val needle = query.trim().lowercase(Locale.ROOT)
        val selected = rows.filter { row ->
            val inBand = when (band) {
                Band.ALL -> true
                Band.GHZ_24 -> row.frequencyMhz in 2400..2500
                Band.GHZ_5 -> row.frequencyMhz in 4900..5924
                Band.GHZ_6 -> row.frequencyMhz in 5925..7125
            }
            inBand && (needle.isEmpty() || listOfNotNull(row.ssid, row.bssid).any { it.lowercase(Locale.ROOT).contains(needle) })
        }
        val comparator = when (order) {
            Order.SIGNAL -> compareBy<Row> { if (it.rssiDbm in -126..0) 0 else 1 }.thenByDescending { it.rssiDbm }
            Order.FREQUENCY -> compareBy<Row> { if (it.frequencyMhz > 0) 0 else 1 }.thenBy { it.frequencyMhz }
            Order.AGE -> compareBy<Row> { if (it.ageSeconds != null && it.ageSeconds >= 0) 0 else 1 }.thenBy { it.ageSeconds ?: Long.MAX_VALUE }
        }
        return selected.sortedWith(comparator.thenBy { it.frequencyMhz }.thenBy { it.ssid.orEmpty() }.thenBy { it.bssid.orEmpty() })
    }
}
