package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.InputFilter
import android.text.InputType
import android.text.TextWatcher
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import java.util.Locale

/** Offline calculations from operator-entered values, never added to captured evidence. */
class WirelessToolsWorkspace(context: Context) : LinearLayout(context) {
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private val pale = Color.parseColor("#b8cbd9")
    private val bright = Color.parseColor("#e8f5fa")
    private val cyan = Color.parseColor("#63d6ee")

    init {
        orientation = VERTICAL
        addText(this, "OFFLINE WIRELESS CALCULATORS", 12f, cyan, true)
        addText(this, "Enter values to calculate. Results are not live measurements and are not saved as evidence.", 13f)
        wifiCard()
        powerCard()
    }

    private fun card(title: String): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL
        setPadding(dp(14), dp(10), dp(14), dp(12))
        background = GradientDrawable().apply { setColor(Color.parseColor("#112335")); cornerRadius = dp(12).toFloat(); setStroke(dp(1), Color.parseColor("#294052")) }
        this@WirelessToolsWorkspace.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(10) })
        addText(this, title, 16f, bright, true)
    }

    private fun addText(parent: LinearLayout, textValue: String, size: Float, color: Int = pale, bold: Boolean = false): TextView = TextView(context).apply {
        text = textValue; textSize = size; setTextColor(color); if (bold) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(5), 0, dp(5)); parent.addView(this)
    }

    private fun input(parent: LinearLayout, label: String, decimal: Boolean): EditText = EditText(context).apply {
        hint = label; contentDescription = label; setSingleLine(true)
        setTextColor(bright); setHintTextColor(pale)
        inputType = InputType.TYPE_CLASS_NUMBER or (if (decimal) InputType.TYPE_NUMBER_FLAG_SIGNED or InputType.TYPE_NUMBER_FLAG_DECIMAL else 0)
        filters = arrayOf(InputFilter.LengthFilter(32)); parent.addView(this)
    }

    private fun button(parent: LinearLayout, label: String, action: () -> Unit): Button = Button(context).apply {
        text = label; isAllCaps = false; minHeight = dp(48); setTextColor(Color.WHITE)
        backgroundTintList = ColorStateList.valueOf(Color.parseColor("#213e56"))
        setOnClickListener { action() }; parent.addView(this)
    }

    private fun clearResultOnEdit(field: EditText, result: TextView, prompt: String) {
        field.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { result.text = prompt }
            override fun afterTextChanged(s: Editable?) {}
        })
    }

    private fun wifiCard() {
        val section = card("Wi-Fi channel ↔ frequency")
        addText(section, "Select the band first: channel numbers overlap between bands.", 13f)
        val band = Spinner(context).apply {
            adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, listOf("2.4 GHz", "5 GHz", "6 GHz"))
            contentDescription = "Wi-Fi band"; section.addView(this)
        }
        val channel = input(section, "Channel number", false)
        val frequency = input(section, "Center frequency (MHz)", false)
        val output = addText(section, "Enter a channel or frequency and choose a direction.", 14f, cyan, true)
        val reset = "Values changed. Choose a direction to recalculate."
        clearResultOnEdit(channel, output, reset); clearResultOnEdit(frequency, output, reset)
        band.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) { output.text = reset }
        }
        fun selected() = WirelessCalculators.Band.entries[band.selectedItemPosition.coerceIn(0, 2)]
        button(section, "Find center frequency") {
            val value = channel.text.toString().trim().toIntOrNull()
            val result = value?.let { WirelessCalculators.channelToMhz(selected(), it) }
            output.text = if (result == null) "Enter a channel in the supported range for the selected band." else "Calculated: channel $value → $result MHz"
        }
        button(section, "Find channel number") {
            val value = frequency.text.toString().trim().toIntOrNull()
            val result = value?.let { WirelessCalculators.mhzToChannel(selected(), it) }
            output.text = if (result == null) "Enter an on-grid whole MHz frequency in the selected band." else "Calculated: $value MHz → channel $result"
        }
        addText(section, "This is a frequency-numbering grid, not a list of valid primary channels. It does not determine bandwidth, availability, local rules, DFS requirements, or permission to transmit. Channel 14 and 6 GHz channel 2 are special cases.", 12f)
        addText(section, "Reference: Android Open Source Project, ScanResult channel conversion (IEEE 802.11 numbering).", 11f)
    }

    private fun powerCard() {
        val section = card("RF power: dBm ↔ mW")
        addText(section, "Convert absolute power; dBm is referenced to 1 mW. Positive values are valid for transmit power.", 13f)
        val dbm = input(section, "Power (dBm)", true)
        val mw = input(section, "Power (mW, greater than zero)", true)
        val output = addText(section, "Enter a value and choose a direction.", 14f, cyan, true)
        val reset = "Values changed. Choose a direction to recalculate."
        clearResultOnEdit(dbm, output, reset); clearResultOnEdit(mw, output, reset)
        button(section, "Convert dBm to mW") {
            val value = dbm.text.toString().trim().toDoubleOrNull()
            val result = value?.let(WirelessCalculators::dbmToMw)
            output.text = if (result == null) "Enter a finite dBm value within the calculator's numeric range." else "Calculated: ${format(value)} dBm = ${format(result)} mW"
        }
        button(section, "Convert mW to dBm") {
            val value = mw.text.toString().trim().toDoubleOrNull()
            val result = value?.let(WirelessCalculators::mwToDbm)
            output.text = if (result == null) "Enter a finite power greater than zero in mW." else "Calculated: ${format(value)} mW = ${format(result)} dBm"
        }
        addText(section, "Formula: mW = 10^(dBm/10); dBm = 10 × log₁₀(mW). These are power units, not antenna gain or signal quality.", 12f)
    }

    private fun format(value: Double): String = String.format(Locale.US, "%.6g", value)
}
