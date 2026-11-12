package com.veilbreaker.companion

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.widget.AdapterView
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView

/** Offline, searchable field notes. The containing page owns vertical scrolling. */
class WirelessReferenceWorkspace(context: Context) : LinearLayout(context) {
    private val results = LinearLayout(context)
    private val search = EditText(context)
    private var category = "All"
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private fun text(value: String, size: Float = 13f, bright: Boolean = false) = TextView(context).apply {
        this.text = value; textSize = size
        setTextColor(Color.parseColor(if (bright) "#e8f5fa" else "#b8cbd9"))
        if (bright) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(4), 0, dp(4))
    }
    init {
        orientation = VERTICAL
        addView(text("FIELD REFERENCE LIBRARY", 16f, true))
        addView(text("Search offline notes by metric, technology, equipment or material. Reference context is not measured evidence.", 12f))
        search.apply {
            hint = "Search: RSRP, BSSID, SINR, concrete…"
            contentDescription = "Search wireless field reference"
            setSingleLine(true); setTextColor(Color.WHITE); setHintTextColor(Color.LTGRAY)
            filters = arrayOf(android.text.InputFilter.LengthFilter(120))
            addTextChangedListener(object : TextWatcher {
                override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { render() }
                override fun afterTextChanged(s: Editable?) {}
            })
        }
        addView(search, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        val categorySpinner = Spinner(context).apply {
            contentDescription = "Reference category"
            adapter = FieldSpinnerAdapter(context, WirelessReferenceLibrary.categories)
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    category = WirelessReferenceLibrary.categories.getOrElse(position) { "All" }; render()
                }
                override fun onNothingSelected(parent: AdapterView<*>?) {}
            }
        }
        addView(categorySpinner, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        results.orientation = VERTICAL
        addView(results, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        render()
    }
    private fun render() {
        results.removeAllViews()
        val found = WirelessReferenceLibrary.search(category, search.text?.toString().orEmpty())
        results.addView(text(if (found.isEmpty()) "No matching references or guides. Try another term or category." else "${found.size} ${if (found.size == 1) "entry" else "entries"} · open a reference to read", 12f))
        found.forEach { entry ->
            val card = LinearLayout(context).apply {
                orientation = VERTICAL; setPadding(dp(12), dp(8), dp(12), dp(10))
                background = GradientDrawable().apply { setColor(Color.parseColor("#112335")); cornerRadius = dp(10).toFloat(); setStroke(dp(1), Color.parseColor("#294052")) }
                setOnClickListener { ReferenceReaderDialog(context, entry).show() }
            }
            results.addView(card, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
            card.addView(text(entry.category.uppercase(), 11f, true).apply { setTextColor(Color.parseColor("#63d6ee")) })
            card.addView(text(entry.title, 15f, true))
            card.addView(text(entry.summary, 13f))
            val open = Button(context).apply {
                this.text = if (entry.category == "Guides") "Open field guide" else "Open reference"
                contentDescription = "${this.text}: ${entry.title}"
                styleFieldButton()
                setOnClickListener { ReferenceReaderDialog(context, entry).show() }
            }
            card.addView(open, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        }
    }
}
