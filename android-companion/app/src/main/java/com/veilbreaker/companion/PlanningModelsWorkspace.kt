package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.InputFilter
import android.text.InputType
import android.text.TextUtils
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
import org.json.JSONObject

/** Compact planning aids using operator input, never device discovery or measured coverage. */
class PlanningModelsWorkspace(context: Context, private val captureProvider: () -> JSONObject? = { null }) : LinearLayout(context) {
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private val bright = Color.parseColor("#e8f5fa")
    private val pale = Color.parseColor("#b8cbd9")
    private val cyan = Color.parseColor("#63d6ee")
    private val drafts = PlanningDraftStore(context)
    private val body = LinearLayout(context).apply { orientation = VERTICAL }

    init {
        orientation = VERTICAL
        text(this, "PLANNING MODELS", 12f, cyan, true)
        text(this, "Offline planning models use entered values. Results are estimates, not captured evidence; verify them on site. Wi-Fi and FWA inputs can be saved explicitly on this phone.", 13f)
        val selector = Spinner(context).apply {
            contentDescription = "Planning model"
            adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item,
                listOf("Wi-Fi AP planning", "Cellular FWA placement & tuning", "Network topology"))
        }
        addView(selector)
        addView(body, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        // Keep drafts while switching models in this workspace session.
        wifi(); fwa(); topology()
        for (index in 1 until body.childCount) body.getChildAt(index).visibility = View.GONE
        selector.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) {}
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                for (index in 0 until body.childCount) body.getChildAt(index).visibility = if (index == position) View.VISIBLE else View.GONE
            }
        }
    }

    private fun text(parent: LinearLayout, value: String, size: Float, color: Int = pale, bold: Boolean = false) = TextView(context).apply {
        text = value; textSize = size; setTextColor(color); if (bold) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(5), 0, dp(5)); parent.addView(this)
    }
    private fun card(title: String, parent: LinearLayout = body): LinearLayout = LinearLayout(context).apply {
        orientation = VERTICAL; setPadding(dp(14), dp(12), dp(14), dp(14))
        background = GradientDrawable().apply { setColor(Color.parseColor("#102638")); cornerRadius = dp(10).toFloat(); setStroke(dp(1), Color.parseColor("#29495a")) }
        parent.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(10) })
        text(this, title, 16f, bright, true)
    }
    private fun input(parent: LinearLayout, label: String, number: Boolean = true, multiline: Boolean = false): EditText {
        text(parent, label, 12f)
        return EditText(context).apply {
            hint = "Enter value"; contentDescription = label; setTextColor(bright); setHintTextColor(pale)
            inputType = if (number) InputType.TYPE_CLASS_NUMBER or InputType.TYPE_NUMBER_FLAG_DECIMAL or InputType.TYPE_NUMBER_FLAG_SIGNED
                else InputType.TYPE_CLASS_TEXT or (if (multiline) InputType.TYPE_TEXT_FLAG_MULTI_LINE else 0)
            if (!multiline) setSingleLine(true) else { minLines = 2; maxLines = 6 }
            filters = arrayOf(InputFilter.LengthFilter(if (multiline) 2048 else 32)); parent.addView(this)
        }
    }
    private fun button(parent: LinearLayout, title: String, action: () -> Unit) = Button(context).apply {
        text = title; isAllCaps = false; minHeight = dp(48); setTextColor(Color.parseColor("#06232a"))
        background = GradientDrawable().apply { setColor(Color.WHITE); cornerRadius = dp(9).toFloat() }
        backgroundTintList = ColorStateList.valueOf(Color.parseColor("#43d7e3"))
        setOnClickListener { action() }; parent.addView(this, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
    }
    private fun invalidateOnEdit(fields: List<EditText>, result: TextView, clear: () -> Unit = {}) {
        fields.forEach { it.addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) { result.text = "Inputs changed. Recalculate to update the estimate."; clear() }
            override fun afterTextChanged(s: Editable?) {}
        }) }
    }
    private fun num(field: EditText) = field.text.toString().trim().toDoubleOrNull()
    private fun fmt(n: Double) = String.format(Locale.US, "%.1f", n)
    private fun draftActions(parent: LinearLayout, save: () -> Boolean, load: () -> Boolean, clear: () -> Boolean) {
        text(parent, "Saved inputs stay on this phone as operator-entered planning data. Loading a draft requires recalculation.", 12f)
        val status = text(parent, "", 12f)
        button(parent, "Save planning inputs") { status.text = if (runCatching(save).getOrDefault(false)) "Planning inputs saved on this phone." else "Could not save: check input ranges or device storage." }
        button(parent, "Load saved inputs") { status.text = if (runCatching(load).getOrDefault(false)) "Saved inputs loaded. Calculate again to refresh the result." else "No usable saved inputs found; existing fields were left unchanged." }
        button(parent, "Delete saved inputs") { status.text = if (runCatching(clear).getOrDefault(false)) "Saved inputs deleted. Current fields remain open." else "Could not delete saved inputs." }
    }

    private fun wifi() {
        val c = card("Wi-Fi AP planning")
        text(c, "Start with capacity and a deliberately idealized circular footprint; validate with a site survey and real client requirements.", 13f)
        val area = input(c, "Floor area (square meters)")
        val radius = input(c, "Assumed usable AP radius (meters)")
        val clients = input(c, "Concurrent clients")
        val perAp = input(c, "Planned clients per AP")
        val result = text(c, "Enter all four inputs and calculate.", 14f, cyan, true)
        val diagram = WifiPlanningDiagram(context).apply { visibility = View.GONE }
        c.addView(diagram, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
        invalidateOnEdit(listOf(area, radius, clients, perAp), result) { diagram.clearEstimate(); diagram.visibility = View.GONE }
        button(c, "Estimate starting AP count") {
            val model = PlanningModels.wifi(num(area) ?: Double.NaN, num(radius) ?: Double.NaN,
                clients.text.toString().trim().toIntOrNull() ?: -1, perAp.text.toString().trim().toIntOrNull() ?: 0)
            result.text = if (model == null) "Enter positive finite area and radius, whole clients ≥ 0 and whole clients per AP > 0."
                else "Ideal area: ${model.areaCount} APs · Capacity: ${model.capacityCount} APs\nStarting estimate: ${model.startingCount} APs"
            if (model != null && diagram.showEstimate(num(area)!!, num(radius)!!, model)) diagram.visibility = View.VISIBLE
            else { diagram.clearEstimate(); diagram.visibility = View.GONE }
        }
        text(c, "Area ÷ πr² ignores overlap, room shape, obstacles, floors, interference, antenna patterns and regulatory limits. This optimistic area count is not a coverage prediction or guarantee. Capacity is the operator's assumption, not a measured limit.", 12f)
        draftActions(c,
            save = { drafts.saveWifi(PlanningWifiDraft(area.text.toString(), radius.text.toString(), clients.text.toString(), perAp.text.toString())) },
            load = { drafts.loadWifi()?.let { area.setText(it.areaM2); radius.setText(it.radiusM); clients.setText(it.clients); perAp.setText(it.clientsPerAp); true } ?: false },
            clear = { drafts.clearWifi() })
    }

    private fun fwa() {
        val c = card("Cellular FWA antenna placement & tuning")
        text(c, "Enter the antenna location and a candidate site's coordinates. A candidate is not proof of your serving tower.", 13f)
        val lat1 = input(c, "Antenna latitude (decimal degrees)")
        val lon1 = input(c, "Antenna longitude (decimal degrees)")
        val lat2 = input(c, "Candidate site latitude (decimal degrees)")
        val lon2 = input(c, "Candidate site longitude (decimal degrees)")
        val frequency = input(c, "Frequency (MHz)")
        val result = text(c, "Enter coordinates and frequency to calculate.", 14f, cyan, true)
        val bearingDiagram = FwaBearingDiagram(context).apply { visibility = View.GONE }
        c.addView(bearingDiagram, LayoutParams(LayoutParams.MATCH_PARENT, dp(190)))
        invalidateOnEdit(listOf(lat1, lon1, lat2, lon2, frequency), result) { bearingDiagram.trueBearing = null; bearingDiagram.visibility = View.GONE }
        button(c, "Estimate direction and free-space loss") {
            val m = PlanningModels.fwa(num(lat1) ?: Double.NaN, num(lon1) ?: Double.NaN,
                num(lat2) ?: Double.NaN, num(lon2) ?: Double.NaN, num(frequency) ?: Double.NaN)
            result.text = if (m == null) "Enter valid distinct, non-antipodal coordinates and a positive frequency."
                else "Great-circle distance: ${fmt(m.distanceKm)} km\nInitial true bearing: ${fmt(m.bearingDegrees)}°\nIdeal free-space loss: ${fmt(m.freeSpaceLossDb)} dB"
            bearingDiagram.trueBearing = m?.bearingDegrees
            bearingDiagram.visibility = if (m == null) View.GONE else View.VISIBLE
        }
        text(c, "Schematic path: antenna ───────── candidate site\nTrue bearing is not a magnetic compass heading; account for local declination. The free-space model assumes unobstructed propagation and does not establish line of sight, tower identity, received power, or service quality.", 12f)
        text(c, "Field tuning: record a baseline; adjust in small steps; allow readings to settle; compare RSRP, RSRQ, SINR and throughput together; record final direction and repeat under similar conditions. Follow equipment and installation safety requirements.", 12f)
        text(c, "Reference: ITU-R P.525-5 (2024), free-space basic transmission loss; spherical great-circle distance approximation.", 11f)
        draftActions(c,
            save = { drafts.saveFwa(PlanningFwaDraft(lat1.text.toString(), lon1.text.toString(), lat2.text.toString(), lon2.text.toString(), frequency.text.toString())) },
            load = { drafts.loadFwa()?.let { lat1.setText(it.antennaLatitude); lon1.setText(it.antennaLongitude); lat2.setText(it.siteLatitude); lon2.setText(it.siteLongitude); frequency.setText(it.frequencyMhz); true } ?: false },
            clear = { drafts.clearFwa() })
        val comparison = FwaTuningWorkspace(context, captureProvider).apply { visibility = View.GONE }
        lateinit var toggle: Button
        toggle = button(c, "Open tuning comparison") {
            val show = comparison.visibility == View.GONE
            comparison.visibility = if (show) View.VISIBLE else View.GONE
            toggle.text = if (show) "Hide tuning comparison" else "Open tuning comparison"
        }
        c.addView(comparison, LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT))
    }

    private fun topology() {
        val group = LinearLayout(context).apply { orientation = VERTICAL; body.addView(this) }
        group.addView(NetworkTopologyWorkspace(context), LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { topMargin = dp(10) })
        val c = card("Separate text-based topology sketch", group).apply { visibility = View.GONE }
        // Move the toggle before the independent text sketch, preserving its original workflow.
        group.removeView(c)
        lateinit var toggle: Button
        toggle = button(group, "Open text-based sketch") {
            val show = c.visibility == View.GONE
            c.visibility = if (show) View.VISIBLE else View.GONE
            toggle.text = if (show) "Hide text-based sketch" else "Open text-based sketch"
        }
        group.addView(c)
        text(c, "This is a separate temporary sketch and does not change the interactive diagram above.", 12f)
        text(c, "Type one device or location per line, then one link per line as A > B. The separator does not imply direction. This is an operator sketch, not discovered network state.", 13f)
        val nodes = input(c, "Nodes, one per line (up to 12)", number = false, multiline = true)
        val links = input(c, "Links, one per line: A > B (up to 30)", number = false, multiline = true)
        val result = text(c, "Enter nodes and links, then draw the schematic.", 14f, cyan, true)
        val diagram = TopologyDiagram(context).apply { visibility = View.GONE }
        c.addView(diagram, LayoutParams(LayoutParams.MATCH_PARENT, dp(260)))
        invalidateOnEdit(listOf(nodes, links), result) { diagram.graph = null; diagram.visibility = View.GONE }
        button(c, "Draw topology") {
            val graph = PlanningModels.topology(nodes.text.toString(), links.text.toString())
            if (graph == null) {
                result.text = "Use 1–12 unique node names (24 characters max); each link must join two different listed nodes only once."
                diagram.visibility = View.GONE
            } else {
                result.text = "Operator schematic · ${graph.nodes.size} nodes · ${graph.links.size} links. Positions are illustrative."
                diagram.graph = graph; diagram.visibility = View.VISIBLE; diagram.invalidate()
            }
        }
        text(c, "Example nodes: Router, Switch, AP (separate lines). Example links: Router > Switch and Switch > AP (separate lines). No connectivity, traffic, VLAN or device identity is verified by this sketch.", 12f)
    }
}

private class TopologyDiagram(context: Context) : View(context) {
    init { isFocusable = true; importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES }
    var graph: PlanningModels.Topology? = null
        set(value) {
            field = value
            contentDescription = if (value == null) "No topology schematic" else {
                val links = value.links.joinToString("; ") { (a, b) -> "${value.nodes[a]} linked to ${value.nodes[b]}" }
                "Operator topology schematic. Nodes: ${value.nodes.joinToString(", ")}. " +
                    if (links.isEmpty()) "No links." else "Links: $links."
            }
            invalidate()
        }
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#4b879d"); strokeWidth = 3f }
    private val node = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#25516a") }
    private val label = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.WHITE; textAlign = Paint.Align.CENTER; typeface = Typeface.DEFAULT_BOLD; textSize = 11 * resources.displayMetrics.scaledDensity }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val model = graph ?: return
        canvas.drawColor(Color.parseColor("#0b1b29"))
        val columns = minOf(3, model.nodes.size)
        val rows = (model.nodes.size + columns - 1) / columns
        val cellWidth = width.toFloat() / columns
        val cellHeight = height.toFloat() / rows
        val points = model.nodes.indices.map { i ->
            ((i % columns + 0.5f) * cellWidth) to ((i / columns + 0.58f) * cellHeight)
        }
        model.links.forEach { (a, b) -> canvas.drawLine(points[a].first, points[a].second, points[b].first, points[b].second, line) }
        model.nodes.forEachIndexed { i, name ->
            val (x, y) = points[i]
            canvas.drawCircle(x, y, 9 * resources.displayMetrics.density, node)
            val shown = TextUtils.ellipsize(name, android.text.TextPaint(label), cellWidth - 8 * resources.displayMetrics.density, TextUtils.TruncateAt.END).toString()
            canvas.drawText(shown, x, (y - 13 * resources.displayMetrics.density).coerceAtLeast(label.textSize), label)
        }
    }
}
