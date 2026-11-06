package com.veilbreaker.companion

/** Session-only trial comparisons with optional provenance from a saved phone observation. */
object FwaTuning {
    data class Sample(val label: String, val bearing: Double, val rsrp: Double?, val rsrq: Double?, val sinr: Double?, val downlink: Double?, val uplink: Double?, val capture: FwaCapturePicker.Candidate? = null)
    data class Difference(val rsrp: Double?, val rsrq: Double?, val sinr: Double?, val downlink: Double?, val uplink: Double?)

    fun sample(label: String, bearing: Double?, rsrp: Double?, rsrq: Double?, sinr: Double?, downlink: Double?, uplink: Double?, capture: FwaCapturePicker.Candidate? = null): Sample? {
        val name = label.trim()
        if (name.isEmpty() || name.length > 60 || name.any(Char::isISOControl) || bearing == null || !bearing.isFinite() || bearing < 0 || bearing >= 360) return null
        val values = listOf(rsrp, rsrq, sinr, downlink, uplink)
        if (values.all { it == null } || values.any { it != null && !it.isFinite() } || (downlink != null && downlink < 0) || (uplink != null && uplink < 0)) return null
        return Sample(name, bearing, rsrp, rsrq, sinr, downlink, uplink, capture)
    }

    fun difference(base: Sample, trial: Sample): Difference {
        fun delta(a: Double?, b: Double?) = if (a != null && b != null) (b - a).takeIf(Double::isFinite) else null
        val compatible = FwaCapturePicker.comparable(base.capture?.context, trial.capture?.context)
        return Difference(if (compatible) delta(base.rsrp, trial.rsrp) else null, if (compatible) delta(base.rsrq, trial.rsrq) else null, if (compatible) delta(base.sinr, trial.sinr) else null, delta(base.downlink, trial.downlink), delta(base.uplink, trial.uplink))
    }
}
