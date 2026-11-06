package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.text.InputFilter
import android.text.InputType
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale

/** Explicit operator input only; does not read or write phone captures. */
class FwaTuningWorkspace(context: Context) : LinearLayout(context) {
    private val trials = mutableListOf<FwaTuning.Sample>()
    private val results = LinearLayout(context).apply { orientation = VERTICAL }
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private fun text(parent: LinearLayout, value: String, size: Float = 13f, emphasis: Boolean = false): TextView = TextView(context).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(if (emphasis) "#69d9e9" else "#b8cbd9")); if (emphasis) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(5), 0, dp(5)); parent.addView(this)
    }
    private fun field(label: String, numeric: Boolean = true): EditText {
        text(this, label, 12f)
        return EditText(context).apply {
            hint = if (numeric) "Optional unless stated" else "Enter position label"; contentDescription = label; setSingleLine(true)
            inputType = if (numeric) InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL or InputType.TYPE_NUMBER_FLAG_SIGNED else InputType.TYPE_CLASS_TEXT
            filters = arrayOf(InputFilter.LengthFilter(if (numeric) 24 else 60)); setTextColor(Color.WHITE); setHintTextColor(Color.parseColor("#a5becb")); this@FwaTuningWorkspace.addView(this)
        }
    }
    private fun action(label: String, block: () -> Unit): Button = Button(context).apply {
        text = label; isAllCaps = false; minHeight = dp(48); setTextColor(Color.WHITE)
        backgroundTintList = ColorStateList.valueOf(Color.parseColor("#233e51")); setOnClickListener { block() }
        this@FwaTuningWorkspace.addView(this, LayoutParams(-1, -2))
    }
    private fun fmt(n: Double) = String.format(Locale.US, "%.1f", n)
    private fun num(field: EditText): Double? = field.text.toString().trim().takeIf { it.isNotEmpty() }?.toDoubleOrNull()
    private fun shown(value: Double?, unit: String) = value?.let { "${fmt(it)} $unit" } ?: "not entered"
    private fun delta(value: Double?, unit: String) = value?.let { String.format(Locale.US, "%+.1f %s", it, unit) } ?: "not comparable"

    init {
        orientation = VERTICAL
        text(this, "FIELD TUNING COMPARISON", 12f, true)
        text(this, "Manually record up to 20 trials. The first is the baseline. Keep technology, band, test target and conditions comparable; the app does not verify them. These entries are session-only operator inputs, not captured evidence.")
        val label = field("Position or trial label", false)
        val bearing = field("Antenna true bearing in degrees (required)")
        val rsrp = field("RSRP (dBm)")
        val rsrq = field("RSRQ (dB)")
        val sinr = field("SINR (dB)")
        val down = field("Downlink (Mbps)")
        val up = field("Uplink (Mbps)")
        val status = text(this, "Enter a label, bearing and at least one metric.")
        action("Add operator trial") {
            val inputs = listOf(bearing, rsrp, rsrq, sinr, down, up)
            if (trials.size >= 20) status.text = "This comparison is limited to 20 trials. Remove the last trial first."
            else if (inputs.any { it.text.toString().isNotBlank() && num(it) == null }) status.text = "Enter numeric values or leave optional fields empty."
            else {
                val sample = FwaTuning.sample(label.text.toString(), num(bearing), num(rsrp), num(rsrq), num(sinr), num(down), num(up))
                if (sample == null) status.text = "Enter a label, a bearing from 0 to less than 360, and at least one finite metric. Throughput cannot be negative."
                else { trials.add(sample); status.text = "Added operator trial ${trials.size}."; render() }
            }
        }
        action("Remove last trial") { if (trials.isNotEmpty()) { trials.removeAt(trials.lastIndex); status.text = "Removed the last operator trial."; render() } }
        addView(results)
        render()
    }

    private fun render() {
        results.removeAllViews()
        if (trials.isEmpty()) { text(results, "No trials in this session."); return }
        val baseline = trials.first()
        trials.forEachIndexed { index, trial ->
            text(results, "${index + 1}. ${trial.label} · ${fmt(trial.bearing)}°${if (index == 0) " · BASELINE" else ""}", 14f, true)
            text(results, "RSRP ${shown(trial.rsrp, "dBm")} · RSRQ ${shown(trial.rsrq, "dB")} · SINR ${shown(trial.sinr, "dB")}\nDown ${shown(trial.downlink, "Mbps")} · Up ${shown(trial.uplink, "Mbps")}")
            if (index > 0) {
                val diff = FwaTuning.difference(baseline, trial)
                text(results, "Change from baseline: RSRP ${delta(diff.rsrp, "dB")}, RSRQ ${delta(diff.rsrq, "dB")}, SINR ${delta(diff.sinr, "dB")}\nDown ${delta(diff.downlink, "Mbps")}, up ${delta(diff.uplink, "Mbps")}", 12f)
            }
        }
    }
}
