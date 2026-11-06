package com.veilbreaker.companion

import android.content.Context
import android.app.AlertDialog
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.InputFilter
import android.text.InputType
import android.text.Editable
import android.text.TextWatcher
import android.widget.ArrayAdapter
import android.widget.AdapterView
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import org.json.JSONObject

/** One-shot lookup; credentials and returned candidate are not saved or added to evidence. */
class OnlineLookupWorkspace(context: Context, private val captureProvider: () -> JSONObject? = { null }) : LinearLayout(context) {
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private var generation = 0

    init {
        orientation = VERTICAL
        val card = LinearLayout(context).apply {
            orientation = VERTICAL; setPadding(dp(14), dp(12), dp(14), dp(14))
            background = GradientDrawable().apply { setColor(Color.parseColor("#102638")); setStroke(dp(1), Color.parseColor("#29495a")); cornerRadius = dp(10).toFloat() }
            this@OnlineLookupWorkspace.addView(this, LayoutParams(-1, -2).apply { topMargin = dp(8) })
        }
        fun text(value: String, size: Float, color: String = "#bed0dd", bold: Boolean = false) = TextView(context).apply {
            this.text = value; textSize = size; setTextColor(Color.parseColor(color)); if (bold) setTypeface(null, Typeface.BOLD)
            setPadding(0, dp(4), 0, dp(4)); card.addView(this)
        }
        fun input(label: String, password: Boolean = false): EditText {
            text(label, 13f, "#e8f5fa")
            return EditText(context).apply {
                hint = "Enter value"; contentDescription = label; setSingleLine(true); setTextColor(Color.WHITE); setHintTextColor(Color.parseColor("#a5becb"))
                inputType = if (password) InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD else InputType.TYPE_CLASS_NUMBER
                filters = arrayOf(InputFilter.LengthFilter(if (password) 256 else 11)); card.addView(this, LayoutParams(-1, -2))
            }
        }
        text("OPENCELLID  /  ONLINE LOOKUP", 13f, "#63d6ee", true)
        text("Look up an entered cell identity in the community database. An account and API key are required; request limits and provider terms apply.", 13f)
        text("Only when you press Look up: your API key and the MCC, MNC, area code, cell ID and radio are sent to OpenCellID over HTTPS. The provider also receives your IP address. No GPS coordinates or measurements are sent. The key is not saved.", 13f)
        val chooseCapture = Button(context).apply {
            this.text = "Choose from last saved capture"; isAllCaps = false; minHeight = dp(48)
            backgroundTintList = ColorStateList.valueOf(Color.parseColor("#233e51")); setTextColor(Color.WHITE)
            card.addView(this, LayoutParams(-1, -2))
        }
        text("Choose a registered LTE/NR cell with a complete identity. This fills the form only; it does not start a lookup.", 12f)
        val key = input("OpenCellID API key", true)
        val mcc = input("MCC (3 digits)")
        val mnc = input("MNC (2 or 3 digits)")
        val area = input("LAC / TAC (decimal)")
        val cell = input("Cell ID (decimal)")
        val radio = Spinner(context).apply {
            adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, listOf("LTE", "NR", "UMTS", "GSM"))
            contentDescription = "Radio technology"; card.addView(this)
        }
        val result = text("Enter the identifiers and choose Look up.", 13f, "#e8f5fa")
        val fields = listOf(key, mcc, mnc, area, cell)
        fields.forEach { field -> field.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { result.text = "Inputs changed. Choose Look up to request a new result." }
            override fun afterTextChanged(s: Editable?) {}
        }) }
        var radioInitialized = false
        radio.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: android.view.View?, position: Int, id: Long) {
                if (radioInitialized) result.text = "Inputs changed. Choose Look up to request a new result."
                radioInitialized = true
            }
        }
        val button = Button(context).apply {
            this.text = "Look up cell"; isAllCaps = false; minHeight = dp(48)
            backgroundTintList = ColorStateList.valueOf(Color.parseColor("#43d7e3")); setTextColor(Color.parseColor("#06232a"))
            card.addView(this, LayoutParams(-1, -2))
        }
        chooseCapture.setOnClickListener {
            val options = runCatching { OpenCellCapturePicker.options(captureProvider()) }.getOrNull()
            if (options == null || options.candidates.isEmpty()) {
                AlertDialog.Builder(context).setTitle("No complete registered cell")
                    .setMessage("The last saved capture has no registered LTE/NR cell with MCC, MNC, TAC and cell ID. Capture again or enter the identifiers manually. No lookup was made.")
                    .setPositiveButton("OK", null).show()
            } else {
                val title = buildString {
                    append("Choose a saved cell")
                    if (options.incomplete > 0) append("\n${options.incomplete} incomplete cell(s) omitted")
                    if (options.truncated) append("\nList limited")
                }
                AlertDialog.Builder(context).setTitle(title)
                    .setItems(options.candidates.map { it.label }.toTypedArray()) { _, index ->
                        val selected = options.candidates[index]
                        mcc.setText(selected.mcc); mnc.setText(selected.mnc); area.setText(selected.area); cell.setText(selected.cellId)
                        radio.setSelection(if (selected.radio == "LTE") 0 else 1)
                        result.text = "Saved cell selected. Review its identity, enter your API key and choose Look up cell."
                    }.setNegativeButton("Cancel", null).show()
            }
        }
        text("Results are community-derived cell-position estimates, not confirmed physical towers. Coverage can be incomplete. Source: OpenCellID, CC BY-SA 4.0 · opencellid.org · creativecommons.org/licenses/by-sa/4.0/", 12f)
        button.setOnClickListener {
            val secret = key.text.toString().trim()
            val query = OpenCellLookup.query(mcc.text.toString().trim(), mnc.text.toString().trim(), area.text.toString().trim(), cell.text.toString().trim(), radio.selectedItem.toString())
            if (secret.isEmpty() || query == null) {
                result.text = "Enter an API key and valid decimal cell identifiers. MCC needs 3 digits; MNC needs 2 or 3."
                return@setOnClickListener
            }
            val request = ++generation
            button.isEnabled = false; chooseCapture.isEnabled = false; fields.forEach { it.isEnabled = false }; radio.isEnabled = false; result.text = "Looking up the entered cell…"
            Thread {
                val answer = OpenCellLookup.lookup(secret, query)
                post {
                    if (request == generation && isAttachedToWindow) { result.text = answer; button.isEnabled = true; chooseCapture.isEnabled = true; fields.forEach { it.isEnabled = true }; radio.isEnabled = true }
                }
            }.start()
        }
    }

    override fun onDetachedFromWindow() {
        generation++
        super.onDetachedFromWindow()
    }
}
