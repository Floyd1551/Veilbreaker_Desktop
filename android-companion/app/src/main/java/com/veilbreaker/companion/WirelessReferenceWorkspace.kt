package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.TextWatcher
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
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
    private var openId: String? = null
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
                override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { openId = null; render() }
                override fun afterTextChanged(s: Editable?) {}
            })
        }
        addView(search, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        val categorySpinner = Spinner(context).apply {
            contentDescription = "Reference category"
            adapter = object : ArrayAdapter<String>(context, android.R.layout.simple_spinner_item, WirelessReferenceLibrary.categories) {
                override fun getView(position: Int, convertView: View?, parent: ViewGroup): View = make(position)
                override fun getDropDownView(position: Int, convertView: View?, parent: ViewGroup): View = make(position)
                private fun make(position: Int): TextView = TextView(context).apply {
                    text = getItem(position); textSize = 14f; setTextColor(Color.parseColor("#e8f5fa"))
                    setBackgroundColor(Color.parseColor("#172a3b")); setPadding(dp(12), dp(12), dp(12), dp(12))
                }
            }
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    category = WirelessReferenceLibrary.categories.getOrElse(position) { "All" }; openId = null; render()
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
        results.addView(text(if (found.isEmpty()) "No matching references or guides. Try another term or category." else "${found.size} ${if (found.size == 1) "entry" else "entries"} · tap to ${if (openId == null) "read" else "expand or collapse"}", 12f))
        found.forEach { entry ->
            val card = LinearLayout(context).apply {
                orientation = VERTICAL; setPadding(dp(12), dp(8), dp(12), dp(10))
                background = GradientDrawable().apply { setColor(Color.parseColor("#112335")); cornerRadius = dp(10).toFloat(); setStroke(dp(1), Color.parseColor("#294052")) }
            }
            results.addView(card, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
            card.addView(text(entry.category.uppercase(), 11f, true).apply { setTextColor(Color.parseColor("#63d6ee")) })
            card.addView(text(entry.title, 15f, true))
            card.addView(text(entry.summary, 13f))
            val toggle = Button(context).apply {
                this.text = if (openId == entry.id) "Hide field notes" else "Read field notes"
                contentDescription = "${this.text}: ${entry.title}"
                isAllCaps = false; minHeight = dp(48)
                backgroundTintList = ColorStateList.valueOf(Color.parseColor("#213e56")); setTextColor(Color.WHITE)
                setOnClickListener { openId = if (openId == entry.id) null else entry.id; render() }
            }
            card.addView(toggle, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
            if (openId == entry.id) {
                card.addView(text("FIELD USE", 11f, true).apply { setTextColor(Color.parseColor("#63d6ee")) })
                card.addView(text(entry.fieldUse))
                card.addView(text("LIMITATIONS", 11f, true).apply { setTextColor(Color.parseColor("#63d6ee")) })
                card.addView(text(entry.limitations))
                card.addView(text("Source: ${entry.sourceName}\n${entry.sourceUrl}\nReference record date: ${entry.reviewed}. Source may change; recheck current rules and specifications.", 11f))
            }
        }
    }
}
