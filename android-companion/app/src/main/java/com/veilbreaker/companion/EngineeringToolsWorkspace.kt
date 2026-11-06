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

/** Searchable offline calculations. Results remain separate from captured evidence. */
class EngineeringToolsWorkspace(context: Context) : LinearLayout(context) {
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private val bright = Color.parseColor("#e8f5fa")
    private val muted = Color.parseColor("#b8cbd9")
    private val cyan = Color.parseColor("#63d6ee")
    private lateinit var selector: Spinner
    private lateinit var editor: LinearLayout
    private lateinit var count: TextView
    private var matches: List<EngineeringToolCatalog.Tool> = emptyList()

    init {
        orientation = VERTICAL
        label(this, "ENGINEERING CALCULATORS", 12f, cyan, true)
        label(this, "Search offline tools by name or subject. Calculations use entered values and are not captured measurements.", 13f)
        val search = EditText(context).apply {
            hint = "Search calculators"; contentDescription = "Search calculators"; setSingleLine(true)
            setTextColor(bright); setHintTextColor(muted); filters = arrayOf(InputFilter.LengthFilter(100))
            this@EngineeringToolsWorkspace.addView(this)
        }
        count = label(this, "", 12f)
        selector = Spinner(context).apply { contentDescription = "Choose engineering calculator"; this@EngineeringToolsWorkspace.addView(this) }
        editor = LinearLayout(context).apply { orientation = VERTICAL; this@EngineeringToolsWorkspace.addView(this) }
        selector.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) { editor.removeAllViews() }
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                matches.getOrNull(position)?.let(::showTool)
            }
        }
        search.addTextChangedListener(watcher { refresh(search.text.toString()) })
        refresh("")
    }

    private fun label(parent: LinearLayout, value: String, size: Float, color: Int = muted, bold: Boolean = false): TextView =
        TextView(context).apply {
            text = value; textSize = size; setTextColor(color); if (bold) setTypeface(null, Typeface.BOLD)
            setPadding(0, dp(4), 0, dp(4)); parent.addView(this)
        }

    private fun watcher(onChange: () -> Unit) = object : TextWatcher {
        override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
        override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { onChange() }
        override fun afterTextChanged(s: Editable?) {}
    }

    private fun refresh(query: String) {
        matches = EngineeringToolCatalog.search(query)
        count.text = if (matches.isEmpty()) "No calculators match. Try another term." else "${matches.size} calculator${if (matches.size == 1) "" else "s"} available"
        selector.visibility = if (matches.isEmpty()) View.GONE else View.VISIBLE
        editor.removeAllViews()
        selector.adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, matches.map { "${it.category} · ${it.title}" })
        matches.firstOrNull()?.let(::showTool)
    }

    private fun showTool(tool: EngineeringToolCatalog.Tool) {
        editor.removeAllViews()
        val card = LinearLayout(context).apply {
            orientation = VERTICAL; setPadding(dp(14), dp(10), dp(14), dp(12))
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#102638")); setStroke(dp(1), Color.parseColor("#29495a")); cornerRadius = dp(10).toFloat()
            }
            editor.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        }
        label(card, tool.title, 17f, bright, true)
        label(card, tool.description, 13f)
        val fields = tool.fields.map { field ->
            label(card, field, 13f, bright)
            EditText(context).apply {
                hint = "Enter value"; contentDescription = field; setSingleLine(true)
                inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_SIGNED or InputType.TYPE_NUMBER_FLAG_DECIMAL
                filters = arrayOf(InputFilter.LengthFilter(32)); setTextColor(bright); setHintTextColor(muted); card.addView(this)
            }
        }
        val result = label(card, "Enter values to calculate.", 14f, cyan, true)
        fields.forEach { field -> field.addTextChangedListener(watcher { result.text = "Inputs changed. Calculate again." }) }
        Button(context).apply {
            text = "Calculate"; isAllCaps = false; minHeight = dp(48); setTextColor(Color.parseColor("#06232a"))
            background = GradientDrawable().apply { setColor(Color.WHITE); cornerRadius = dp(9).toFloat() }
            backgroundTintList = ColorStateList.valueOf(Color.parseColor("#43d7e3"))
            setOnClickListener {
                val values = fields.map { it.text.toString().trim().toDoubleOrNull() }
                val answer = if (values.any { it == null }) null else tool.evaluate(values.filterNotNull())
                result.text = if (answer == null) "Enter finite values within the ranges described above." else
                    "Calculated: ${String.format(Locale.US, "%.6g", answer)} ${tool.unit}"
            }
            card.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(6) })
        }
        label(card, "Calculated from operator inputs · not saved as evidence", 11f)
    }
}
