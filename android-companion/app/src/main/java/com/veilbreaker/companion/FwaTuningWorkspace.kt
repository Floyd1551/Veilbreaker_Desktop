package com.veilbreaker.companion

import android.app.AlertDialog
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
import org.json.JSONObject

/** Session-only comparisons from operator inputs and explicitly selected saved captures. */
class FwaTuningWorkspace(context: Context, private val captureProvider: () -> JSONObject? = { null }) : LinearLayout(context) {
    private var selectedCapture: FwaCapturePicker.Candidate? = null
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
        text(this, "Record up to 20 session-only trials. The first is the baseline. You may explicitly copy values from a saved phone capture; these are past observations, not current readings. Keep technology, band, test target and conditions comparable; missing identity does not prove comparability.")
        val label = field("Position or trial label", false)
        val bearing = field("Antenna true bearing in degrees (required)")
        val rsrp = field("RSRP (dBm)")
        val rsrq = field("RSRQ (dB)")
        val sinr = field("SINR (dB)")
        val captureStatus = text(this, "No saved observation selected. Signal fields are operator inputs.")
        action("Choose saved cellular observation") {
            val options = runCatching { FwaCapturePicker.options(captureProvider()) }.getOrNull()
            if (options == null || options.candidates.isEmpty()) {
                captureStatus.text = "No usable saved LTE or NR observation is available. No new measurement was requested."
            } else {
                val labels = options.candidates.map { candidate -> candidate.description +
                    "\nRSRP ${shown(candidate.rsrp, "dBm")} | RSRQ ${shown(candidate.rsrq, "dB")} | SINR ${shown(candidate.sinr, "dB")}" }.toTypedArray()
                AlertDialog.Builder(context).setTitle(if (options.truncated) "Saved observations (list limited)" else "Choose a saved observation")
                    .setItems(labels) { _, index ->
                        val candidate = options.candidates[index]
                        selectedCapture = candidate
                        rsrp.setText(candidate.rsrp?.toString() ?: "")
                        rsrq.setText(candidate.rsrq?.toString() ?: "")
                        sinr.setText(candidate.sinr?.toString() ?: "")
                        captureStatus.text = "Selected past observation:\n${candidate.description}\nSignal fields can be edited; original captured values remain in the trial context."
                    }.setNegativeButton("Cancel", null).show()
            }
        }
        action("Clear selected observation") {
            selectedCapture = null
            rsrp.setText(""); rsrq.setText(""); sinr.setText("")
            captureStatus.text = "No saved observation selected. Signal fields are operator inputs."
        }
        val down = field("Downlink (Mbps)")
        val up = field("Uplink (Mbps)")
        val status = text(this, "Enter a label, bearing and at least one metric.")
        action("Add operator trial") {
            val inputs = listOf(bearing, rsrp, rsrq, sinr, down, up)
            if (trials.size >= 20) status.text = "This comparison is limited to 20 trials. Remove the last trial first."
            else if (inputs.any { it.text.toString().isNotBlank() && num(it) == null }) status.text = "Enter numeric values or leave optional fields empty."
            else {
                val sample = FwaTuning.sample(label.text.toString(), num(bearing), num(rsrp), num(rsrq), num(sinr), num(down), num(up), selectedCapture)
                if (sample == null) status.text = "Enter a label, a bearing from 0 to less than 360, and at least one finite metric. Throughput cannot be negative."
                else {
                    trials.add(sample); status.text = "Added trial ${trials.size}."; render()
                    if (selectedCapture != null) {
                        selectedCapture = null; rsrp.setText(""); rsrq.setText(""); sinr.setText("")
                        captureStatus.text = "No saved observation selected. Signal fields are operator inputs."
                    }
                }
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
            trial.capture?.let { captured ->
                text(results, "Selected saved observation (past context):\n${captured.description}\nOriginal captured values: RSRP ${shown(captured.rsrp, "dBm")} | RSRQ ${shown(captured.rsrq, "dB")} | SINR ${shown(captured.sinr, "dB")}" +
                    if (trial.rsrp != captured.rsrp || trial.rsrq != captured.rsrq || trial.sinr != captured.sinr) "\nTrial signal values were edited by the operator." else "", 12f)
            }
            if (index > 0) {
                if (!FwaCapturePicker.comparable(baseline.capture?.context, trial.capture?.context))
                    text(results, "Cellular changes suppressed: known capture technology, subscription or identity differs. Throughput changes still require comparable test conditions.", 12f)
                val diff = FwaTuning.difference(baseline, trial)
                text(results, "Change from baseline: RSRP ${delta(diff.rsrp, "dB")}, RSRQ ${delta(diff.rsrq, "dB")}, SINR ${delta(diff.sinr, "dB")}\nDown ${delta(diff.downlink, "Mbps")}, up ${delta(diff.uplink, "Mbps")}", 12f)
            }
        }
    }
}
