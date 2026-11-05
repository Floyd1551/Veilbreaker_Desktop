package com.veilbreaker.companion

/** Groups Android cached observations by reported primary center frequency, not inferred width. */
object WifiChannelPlotModel {
    enum class Band(val title: String, val minMhz: Int, val maxMhz: Int) {
        GHZ_24("2.4 GHz", 2400, 2500), GHZ_5("5 GHz", 4900, 5924), GHZ_6("6 GHz", 5925, 7125)
    }
    data class Sample(val frequencyMhz: Int, val rssiDbm: Int, val ageSeconds: Long?)
    data class Point(
        val band: Band, val frequencyMhz: Int, val strongestDbm: Int, val observationCount: Int,
        val youngestSeconds: Long?, val oldestSeconds: Long?, val ageUnavailableCount: Int
    )
    fun aggregate(samples: List<Sample>): List<Point> = samples.asSequence()
        .filter { it.rssiDbm in -126..0 && Band.entries.any { band -> it.frequencyMhz in band.minMhz..band.maxMhz } }
        .groupBy { it.frequencyMhz }.map { (frequency, values) ->
            val ages = values.mapNotNull { it.ageSeconds?.takeIf { age -> age >= 0 } }
            Point(Band.entries.first { frequency in it.minMhz..it.maxMhz }, frequency,
                values.maxOf { it.rssiDbm }, values.size, ages.minOrNull(), ages.maxOrNull(), values.size - ages.size)
        }.sortedBy { it.frequencyMhz }
}
