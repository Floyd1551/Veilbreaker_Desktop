package com.veilbreaker.companion

import android.content.Context
import android.content.ClipData
import android.content.ClipboardManager
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
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import android.widget.Toast
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
    private val state = ToolWorkspaceState()
    private var displayedToolId: String? = null
    private var changingSelection = false

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
            override fun onNothingSelected(parent: AdapterView<*>?) {
                if (matches.isEmpty()) { editor.removeAllViews(); displayedToolId = null }
            }
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (changingSelection) return
                matches.getOrNull(position)?.let { tool ->
                    state.select(tool.id)
                    if (displayedToolId != tool.id) showTool(tool)
                }
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
        val selectedIndex = state.indexFor(matches.map { it.id })
        changingSelection = true
        selector.adapter = FieldSpinnerAdapter(context, matches.map { "${it.category} · ${it.title}" })
        if (selectedIndex >= 0) selector.setSelection(selectedIndex)
        changingSelection = false
        if (selectedIndex < 0) { editor.removeAllViews(); displayedToolId = null }
        else if (displayedToolId != matches[selectedIndex].id) showTool(matches[selectedIndex])
    }

    private fun showTool(tool: EngineeringToolCatalog.Tool) {
        editor.removeAllViews()
        displayedToolId = tool.id
        val card = LinearLayout(context).apply {
            orientation = VERTICAL; setPadding(dp(14), dp(10), dp(14), dp(12))
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#102638")); setStroke(dp(1), Color.parseColor("#29495a")); cornerRadius = dp(10).toFloat()
            }
            editor.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        }
        label(card, tool.title, 17f, bright, true)
        label(card, tool.description, 13f)
        val visual = ToolVisualModel.forTool(tool.id)?.let { spec ->
            val diagram = EngineeringToolDiagram(context, tool.id, spec)
            card.addView(diagram, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(6) })
            label(card, spec.description, 12f)
            diagram
        }
        val fields = tool.fields.map { field ->
            label(card, field, 13f, bright)
            EditText(context).apply {
                hint = "Enter value"; contentDescription = field; setSingleLine(true)
                inputType = InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_SIGNED or InputType.TYPE_NUMBER_FLAG_DECIMAL
                filters = arrayOf(InputFilter.LengthFilter(32)); setTextColor(bright); setHintTextColor(muted); card.addView(this)
            }
        }
        val result = label(card, "Enter values to calculate.", 14f, cyan, true)
        val worksheet = LinearLayout(context).apply { orientation = VERTICAL; visibility = View.GONE; card.addView(this) }
        var calculatedInputs: List<String>? = null
        var worksheetText: String? = null
        val copy = Button(context).apply {
            text = "Copy worksheet"; isAllCaps = false; minHeight = dp(48); isEnabled = false
            background = GradientDrawable().apply { setColor(Color.WHITE); cornerRadius = dp(9).toFloat() }
            val states = arrayOf(intArrayOf(-android.R.attr.state_enabled), intArrayOf())
            backgroundTintList = ColorStateList(states, intArrayOf(Color.parseColor("#1b2935"), Color.parseColor("#233e51")))
            setTextColor(ColorStateList(states, intArrayOf(Color.parseColor("#8ca0ae"), bright)))
            setOnClickListener {
                val currentInputs = fields.map { it.text.toString().trim() }
                val textToCopy = worksheetText
                if (textToCopy != null && calculatedInputs == currentInputs) {
                    val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                    clipboard.setPrimaryClip(ClipData.newPlainText("Calculated worksheet", textToCopy))
                    Toast.makeText(context, "Worksheet copied", Toast.LENGTH_SHORT).show()
                }
            }
        }
        val draft = state.draft(tool.id)
        fields.forEachIndexed { index, field -> if (index < draft.size) field.setText(draft[index]) }
        fields.forEach { field -> field.addTextChangedListener(watcher {
            state.saveDraft(tool.id, fields.map { it.text.toString() })
            result.text = "Inputs changed. Calculate again."
            calculatedInputs = null; worksheetText = null; copy.isEnabled = false
            worksheet.removeAllViews(); worksheet.visibility = View.GONE; visual?.clearCalculation()
        }) }
        Button(context).apply {
            text = "Calculate"; isAllCaps = false; minHeight = dp(48); setTextColor(Color.parseColor("#06232a"))
            background = GradientDrawable().apply { setColor(Color.WHITE); cornerRadius = dp(9).toFloat() }
            backgroundTintList = ColorStateList.valueOf(Color.parseColor("#43d7e3"))
            setOnClickListener {
                calculatedInputs = null; worksheetText = null; copy.isEnabled = false
                val inputText = fields.map { it.text.toString().trim() }
                val values = inputText.map { it.toDoubleOrNull() }
                val answer = if (values.any { it == null }) null else tool.evaluate(values.filterNotNull())
                result.text = if (answer == null) "Enter finite values within the ranges described above." else
                    "Calculated: ${String.format(Locale.US, "%.6g", answer)} ${tool.unit}"
                worksheet.removeAllViews()
                if (answer == null) { worksheet.visibility = View.GONE; visual?.clearCalculation() }
                else {
                    val safeValues = values.filterNotNull()
                    visual?.showCalculation(safeValues)
                    label(worksheet, "CALCULATION WORKSHEET", 11f, cyan, true)
                    fun row(name: String, value: String) {
                        val line = LinearLayout(context).apply { orientation = HORIZONTAL; setPadding(0, dp(3), 0, dp(3)) }
                        worksheet.addView(line, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
                        val key = TextView(context).apply { text = name; textSize = 12f; setTextColor(muted) }
                        val amount = TextView(context).apply { text = value; textSize = 12f; setTextColor(bright); gravity = android.view.Gravity.END }
                        line.addView(key, LayoutParams(0, LayoutParams.WRAP_CONTENT, 2f))
                        line.addView(amount, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f))
                    }
                    tool.fields.forEachIndexed { index, name -> row(name, fields[index].text.toString().trim()) }
                    val formattedAnswer = "${String.format(Locale.US, "%.6g", answer)} ${tool.unit}"
                    row("Calculated result", formattedAnswer)
                    calculatedInputs = inputText
                    worksheetText = buildString {
                        appendLine("${tool.title} — calculation worksheet")
                        appendLine("Calculated from operator inputs; not a measurement or captured evidence.")
                        appendLine("Operator inputs:")
                        tool.fields.forEachIndexed { index, name -> appendLine("$name: ${inputText[index]}") }
                        appendLine("Calculated result: $formattedAnswer")
                        append("Assumptions and limitations: ${tool.description}")
                    }
                    copy.isEnabled = true
                    worksheet.visibility = View.VISIBLE
                }
            }
            card.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(6) })
        }
        card.addView(copy, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        label(card, "Calculated from operator inputs · not saved as evidence", 11f)
    }
}
