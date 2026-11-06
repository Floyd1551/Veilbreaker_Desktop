package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.InputFilter
import android.text.TextPaint
import android.text.TextUtils
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import kotlin.math.hypot

/** An operator-authored topology sketch. No discovery, measured link state or automatic persistence. */
class NetworkTopologyWorkspace(context: Context) : LinearLayout(context) {
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    private val pale = Color.parseColor("#b8cbd9")
    private val bright = Color.parseColor("#e8f5fa")
    private val cyan = Color.parseColor("#63d6ee")
    private var state = TopologyEditor.State()
    private val history = ArrayDeque<TopologyEditor.State>()
    private lateinit var diagram: InteractiveTopologyDiagram
    private lateinit var nodePicker: Spinner
    private lateinit var fromPicker: Spinner
    private lateinit var toPicker: Spinner
    private lateinit var details: TextView
    private lateinit var status: TextView
    private lateinit var undo: Button
    private var selected = -1
    private var updating = false

    init {
        orientation = VERTICAL
        setPadding(dp(14), dp(12), dp(14), dp(14))
        background = GradientDrawable().apply {
            setColor(Color.parseColor("#102638")); setStroke(dp(1), Color.parseColor("#29495a")); cornerRadius = dp(10).toFloat()
        }
        label("Network topology sketch", 16f, bright, true)
        label("Build a diagram by adding nodes and undirected links. Tap a node or use the selector for details. This is an operator sketch, not network discovery or verified link status. Drafts are not saved between app sessions.", 13f)
        diagram = InteractiveTopologyDiagram(context) { index ->
            if (index in state.nodes.indices) { selected = index; nodePicker.setSelection(index); updateDetails() }
        }
        addView(diagram, LayoutParams(LayoutParams.MATCH_PARENT, dp(180)).apply { topMargin = dp(8) })
        label("Selected node", 13f, bright)
        nodePicker = spinner("Select topology node")
        details = label("Add a node to begin.", 13f)
        nodePicker.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (!updating && position in state.nodes.indices) { selected = position; updateDetails() }
            }
        }
        label("Node name", 13f, bright)
        val name = EditText(context).apply {
            hint = "Device or location"; contentDescription = "New topology node name"; setSingleLine(true)
            setTextColor(bright); setHintTextColor(pale); filters = arrayOf(InputFilter.LengthFilter(24))
            this@NetworkTopologyWorkspace.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        }
        status = label("Add up to 12 nodes and 30 links.", 13f, cyan)
        action("Add node") {
            val next = TopologyEditor.addNode(state, name.text.toString())
            if (next == null) status.text = "Use a unique name of 1–24 characters; up to 12 nodes."
            else { commit(next); selected = state.nodes.lastIndex; name.text.clear(); refresh(); status.text = "Node added to operator sketch." }
        }
        action("Remove selected node") {
            val next = TopologyEditor.removeNode(state, selected)
            if (next == null) status.text = "Select a node first."
            else { commit(next); selected = if (state.nodes.isEmpty()) -1 else selected.coerceIn(state.nodes.indices); refresh(); status.text = "Node and its links removed. Undo is available." }
        }
        label("Link endpoints", 13f, bright, true)
        label("Endpoint A", 12f, pale)
        fromPicker = spinner("Link endpoint A")
        label("Endpoint B", 12f, pale)
        toPicker = spinner("Link endpoint B")
        action("Add link") {
            val next = TopologyEditor.addLink(state, fromPicker.selectedItemPosition, toPicker.selectedItemPosition)
            if (next == null) status.text = "Choose two different nodes without an existing link; limit 30 links."
            else { commit(next); refresh(); status.text = "Undirected operator link added." }
        }
        action("Remove link between endpoints") {
            val next = TopologyEditor.removeLink(state, fromPicker.selectedItemPosition, toPicker.selectedItemPosition)
            if (next == null) status.text = "There is no link between the selected endpoints."
            else { commit(next); refresh(); status.text = "Link removed. Undo is available." }
        }
        undo = action("Undo last edit") {
            if (history.isEmpty()) status.text = "Nothing to undo."
            else {
                state = history.removeLast(); selected = if (state.nodes.isEmpty()) -1 else selected.coerceIn(state.nodes.indices)
                refresh(); status.text = "Previous sketch restored."
            }
        }
        label("Lines and positions are schematic. They do not show device health, direction, interface, VLAN, traffic, cable length or measured connectivity.", 12f)
        refresh()
    }

    private fun label(value: String, size: Float, color: Int = pale, bold: Boolean = false) = TextView(context).apply {
        text = value; textSize = size; setTextColor(color); if (bold) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(5), 0, dp(5)); this@NetworkTopologyWorkspace.addView(this)
    }

    private fun action(title: String, click: () -> Unit) = Button(context).apply {
        text = title; isAllCaps = false; minHeight = dp(48); setTextColor(bright)
        background = GradientDrawable().apply { setColor(Color.WHITE); cornerRadius = dp(8).toFloat() }
        backgroundTintList = ColorStateList.valueOf(Color.parseColor("#1c4357"))
        setOnClickListener { click() }; this@NetworkTopologyWorkspace.addView(this, LayoutParams(-1, -2).apply { topMargin = dp(4) })
    }

    private fun spinner(description: String) = Spinner(context).apply {
        contentDescription = description
        this@NetworkTopologyWorkspace.addView(this, LayoutParams(-1, -2))
    }

    private fun adapter(values: List<String>) = object : ArrayAdapter<String>(context, android.R.layout.simple_spinner_item, values) {
        override fun getView(position: Int, convertView: View?, parent: ViewGroup): View = row(position)
        override fun getDropDownView(position: Int, convertView: View?, parent: ViewGroup): View = row(position)
        private fun row(position: Int): TextView = TextView(context).apply {
            text = getItem(position); textSize = 14f; setTextColor(bright)
            setBackgroundColor(Color.parseColor("#172f40")); setPadding(dp(12), dp(12), dp(12), dp(12))
        }
    }

    private fun commit(next: TopologyEditor.State) {
        if (history.size == 20) history.removeFirst()
        history.addLast(state); state = next
    }

    private fun refresh() {
        val a = fromPicker.selectedItemPosition.coerceAtLeast(0)
        val b = toPicker.selectedItemPosition.coerceAtLeast(0)
        val names = state.nodes.ifEmpty { listOf("No nodes yet") }
        updating = true
        for (picker in listOf(nodePicker, fromPicker, toPicker)) { picker.adapter = adapter(names); picker.isEnabled = state.nodes.isNotEmpty() }
        if (selected !in state.nodes.indices) selected = if (state.nodes.isEmpty()) -1 else 0
        nodePicker.setSelection(selected.coerceAtLeast(0))
        fromPicker.setSelection(a.coerceIn(0, names.lastIndex))
        val bIndex = b.coerceIn(0, names.lastIndex)
        toPicker.setSelection(if (state.nodes.size > 1 && bIndex == a) (bIndex + 1) % state.nodes.size else bIndex)
        updating = false
        undo.isEnabled = history.isNotEmpty()
        val columns = if (resources.configuration.screenWidthDp < 360) 2 else 3
        val rows = maxOf(1, (state.nodes.size + columns - 1) / columns)
        diagram.layoutParams = diagram.layoutParams.apply { height = dp(maxOf(180, rows * 76)) }
        updateDetails()
    }

    private fun updateDetails() {
        val title = state.nodes.getOrNull(selected)
        details.text = if (title == null) "Add a node to begin." else {
            val neighbors = TopologyEditor.neighbors(state, selected)
            "Selected: $title\n" + if (neighbors.isEmpty()) "No drawn links." else "Drawn links: ${neighbors.joinToString(", ")}"
        }
        diagram.update(state, selected)
    }
}

private class InteractiveTopologyDiagram(context: Context, private val onSelect: (Int) -> Unit) : View(context) {
    private fun dp(n: Int) = n * resources.displayMetrics.density
    private var state = TopologyEditor.State()
    private var selected = -1
    private val linkPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#4b879d"); strokeWidth = dp(2) }
    private val nodePaint = Paint(Paint.ANTI_ALIAS_FLAG)
    private val labelPaint = TextPaint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; textAlign = Paint.Align.CENTER; textSize = 12 * resources.displayMetrics.scaledDensity; typeface = Typeface.DEFAULT_BOLD }
    private var points = emptyList<Pair<Float, Float>>()

    init { isClickable = true; isFocusable = true; importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES }

    fun update(value: TopologyEditor.State, selection: Int) {
        state = value; selected = selection
        val links = value.links.joinToString("; ") { (a, b) -> "${value.nodes[a]} linked to ${value.nodes[b]}" }
        contentDescription = "Operator topology diagram. Nodes: ${value.nodes.joinToString(", ").ifEmpty { "none" }}. " +
            if (links.isEmpty()) "No links. Use the node selector for accessible details." else "Links: $links. Use the node selector for accessible details."
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas); canvas.drawColor(Color.parseColor("#0b1b29"))
        if (state.nodes.isEmpty()) {
            points = emptyList()
            canvas.drawText("No nodes yet", width / 2f, height / 2f - dp(4), labelPaint)
            canvas.drawText("Add a node below to begin", width / 2f, height / 2f + dp(18), labelPaint)
            return
        }
        val columns = minOf(if (resources.configuration.screenWidthDp < 360) 2 else 3, state.nodes.size)
        val rows = (state.nodes.size + columns - 1) / columns
        val cellWidth = width.toFloat() / columns; val cellHeight = height.toFloat() / rows
        points = state.nodes.indices.map { i -> ((i % columns + 0.5f) * cellWidth) to ((i / columns + 0.62f) * cellHeight) }
        state.links.forEach { (a, b) -> canvas.drawLine(points[a].first, points[a].second, points[b].first, points[b].second, linkPaint) }
        state.nodes.forEachIndexed { i, name ->
            val (x, y) = points[i]
            nodePaint.color = Color.parseColor(if (i == selected) "#52dce4" else "#3a7d94")
            canvas.drawCircle(x, y, dp(10), nodePaint)
            val shown = TextUtils.ellipsize(name, labelPaint, (cellWidth - dp(8)).coerceAtLeast(0f), TextUtils.TruncateAt.END).toString()
            canvas.drawText(shown, x, (y - dp(16)).coerceAtLeast(labelPaint.textSize), labelPaint)
        }
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.action == MotionEvent.ACTION_UP) {
            val nearest = points.indices.minByOrNull { i -> hypot(points[i].first - event.x, points[i].second - event.y) }
            if (nearest != null && hypot(points[nearest].first - event.x, points[nearest].second - event.y) <= dp(32)) {
                onSelect(nearest); performClick()
            }
        }
        return true
    }
    override fun performClick(): Boolean { super.performClick(); return true }
}
