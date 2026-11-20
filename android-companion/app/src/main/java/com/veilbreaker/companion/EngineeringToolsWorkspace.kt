package com.veilbreaker.companion

import android.content.Context
import android.content.ClipData
import android.content.ClipboardManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.Rect
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.content.res.ColorStateList
import android.text.Editable
import android.text.InputFilter
import android.text.InputType
import android.text.TextWatcher
import android.view.View
import android.view.inputmethod.InputMethodManager
import android.widget.AdapterView
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import java.util.Locale

/** Searchable offline calculations. Results remain separate from captured evidence. */
class EngineeringToolsWorkspace(context: Context) : LinearLayout(context) {
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private val bright = Color.parseColor("#edf5f8")
    private val muted = Color.parseColor("#b8cbd9")
    private val cyan = Color.parseColor("#78d8db")
    private lateinit var browser: LinearLayout
    private lateinit var search: EditText
    private lateinit var results: LinearLayout
    private lateinit var editor: LinearLayout
    private lateinit var count: TextView
    private var category = "All categories"
    private val state = ToolWorkspaceState()

    init {
        orientation = VERTICAL
        label(this, "Engineering calculators", 16f, bright, true)
        label(this, "Find an offline calculator for the task at hand.", 13f)
        browser = LinearLayout(context).apply { orientation = VERTICAL; this@EngineeringToolsWorkspace.addView(this) }
        search = EditText(context).apply {
            hint = "Search calculators"; contentDescription = "Search calculators"; setSingleLine(true)
            setTextColor(bright); setHintTextColor(muted); filters = arrayOf(InputFilter.LengthFilter(100))
            browser.addView(this)
        }
        val categories = listOf("All categories") + EngineeringToolCatalog.tools.map { it.category }.distinct().sorted()
        Spinner(context).apply {
            contentDescription = "Calculator category"
            adapter = FieldSpinnerAdapter(context, categories)
            onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent: AdapterView<*>?) {}
                override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                    category = categories.getOrElse(position) { "All categories" }
                    refresh()
                }
            }
            browser.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        }
        count = label(browser, "", 12f)
        results = LinearLayout(context).apply { orientation = VERTICAL; browser.addView(this) }
        editor = LinearLayout(context).apply { orientation = VERTICAL; visibility = View.GONE; this@EngineeringToolsWorkspace.addView(this) }
        search.addTextChangedListener(watcher { refresh() })
        refresh()
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

    private fun revealWorkspace() {
        post {
            var ancestor = parent
            while (ancestor != null && ancestor !is ScrollView) ancestor = ancestor.parent
            (ancestor as? ScrollView)?.let { scroll ->
                val bounds = Rect(0, 0, width, height)
                scroll.offsetDescendantRectToMyCoords(this, bounds)
                scroll.smoothScrollTo(0, bounds.top)
            }
        }
    }

    private fun refresh() {
        if (!::results.isInitialized) return
        val matches = EngineeringToolCatalog.search(search.text.toString())
            .filter { category == "All categories" || it.category == category }
        count.text = if (matches.isEmpty()) "No calculators found. Try another search or category."
            else "${matches.size} calculator${if (matches.size == 1) "" else "s"} · tap to open"
        results.removeAllViews()
        matches.forEach { tool ->
            val categoryColor = Color.parseColor(when (tool.category) {
                "Cellular" -> "#a8c9ff"
                "Wi-Fi" -> "#8ce0d5"
                "Networking" -> "#c1b9f5"
                "Fiber & Power" -> "#e9c58b"
                else -> "#78d8db"
            })
            val tile = LinearLayout(context).apply {
                orientation = VERTICAL; setPadding(dp(16), dp(10), dp(16), dp(10)); minimumHeight = dp(64)
                val shape = GradientDrawable().apply { setColor(Color.parseColor("#142a39")); cornerRadius = dp(16).toFloat() }
                background = RippleDrawable(ColorStateList.valueOf(Color.parseColor("#365b66")), shape, null)
                isClickable = true; isFocusable = true
                contentDescription = "${tool.title}, ${tool.category} calculator. ${tool.description} Open calculator."
                accessibilityDelegate = object : View.AccessibilityDelegate() {
                    override fun onInitializeAccessibilityNodeInfo(host: View, info: android.view.accessibility.AccessibilityNodeInfo) {
                        super.onInitializeAccessibilityNodeInfo(host, info); info.className = Button::class.java.name
                    }
                }
                setOnClickListener {
                    (context.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager).hideSoftInputFromWindow(search.windowToken, 0)
                    search.clearFocus(); state.select(tool.id); browser.visibility = View.GONE; editor.visibility = View.VISIBLE
                    showTool(tool); revealWorkspace()
                }
                results.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
            }
            label(tile, tool.category, 11f, categoryColor, true).importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            label(tile, "${tool.title}  ›", 15f, bright, true).importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            label(tile, tool.description, 12f).apply {
                maxLines = 2
                ellipsize = android.text.TextUtils.TruncateAt.END
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
            }
        }
    }

    fun closeDetail(): Boolean {
        if (!::editor.isInitialized || editor.visibility != View.VISIBLE) return false
        (context.getSystemService(Context.INPUT_METHOD_SERVICE) as InputMethodManager)
            .hideSoftInputFromWindow(editor.windowToken, 0)
        editor.findFocus()?.clearFocus()
        editor.visibility = View.GONE; browser.visibility = View.VISIBLE; revealWorkspace()
        return true
    }

    private fun showTool(tool: EngineeringToolCatalog.Tool) {
        editor.removeAllViews()
        Button(context).apply {
            text = "‹  All calculators"; styleFieldButton()
            contentDescription = "Back to calculator list"
            setOnClickListener { closeDetail() }
            editor.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        }
        val card = LinearLayout(context).apply {
            orientation = VERTICAL; setPadding(dp(16), dp(14), dp(16), dp(16))
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#142532")); setStroke(dp(1), Color.parseColor("#263c49")); cornerRadius = dp(16).toFloat()
            }
            editor.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(8) })
        }
        label(card, tool.category.uppercase(Locale.ROOT), 11f, cyan, true)
        label(card, tool.title, 20f, bright, true)
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
            text = "Copy worksheet"; styleFieldButton(); isEnabled = false
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
            text = "Calculate"; styleFieldButton(primary = true)
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
                    label(worksheet, "Calculation worksheet", 12f, cyan, true)
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
