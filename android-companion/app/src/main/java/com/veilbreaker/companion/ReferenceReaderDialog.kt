package com.veilbreaker.companion

import android.app.Dialog
import android.content.Context
import android.graphics.Color
import android.graphics.Rect
import android.graphics.Typeface
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.GradientDrawable
import android.view.KeyEvent
import android.view.View
import android.view.ViewGroup
import android.view.Window
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView

/** Full-screen offline reader; navigating references never changes captured evidence. */
internal class ReferenceReaderDialog(context: Context, initial: WirelessReferenceLibrary.Entry) : Dialog(context) {
    private val history = mutableListOf(initial)
    private val content = LinearLayout(context)
    private val scroll = ScrollView(context)
    private val back = Button(context)
    private fun dp(n: Int) = (n * context.resources.displayMetrics.density).toInt()

    init {
        requestWindowFeature(Window.FEATURE_NO_TITLE)
        val root = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#09141f"))
            setPadding(dp(16), dp(8), dp(16), dp(8))
        }
        back.apply {
            styleFieldButton(); text = "Back to references"
            setOnClickListener { goBack() }
        }
        root.addView(back, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))
        content.orientation = LinearLayout.VERTICAL
        content.setPadding(0, dp(8), 0, dp(24))
        scroll.isFillViewport = true
        scroll.addView(content)
        root.addView(scroll, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f))
        setContentView(root)
        setOnKeyListener { _, key, event ->
            if (key == KeyEvent.KEYCODE_BACK && event.action == KeyEvent.ACTION_UP) { goBack(); true } else key == KeyEvent.KEYCODE_BACK
        }
        render()
    }

    override fun show() {
        super.show()
        window?.setBackgroundDrawable(ColorDrawable(Color.parseColor("#09141f")))
        window?.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
    }

    private fun goBack() {
        if (history.size == 1) dismiss() else { history.removeAt(history.lastIndex); render() }
    }
    private fun addText(value: String, size: Float = 14f, color: String = "#c1d4df", bold: Boolean = false, parent: LinearLayout = content): TextView {
        return TextView(context).apply {
            text = value; textSize = size; setTextColor(Color.parseColor(color)); setTextIsSelectable(true)
            setPadding(0, dp(5), 0, dp(7)); setLineSpacing(dp(2).toFloat(), 1f)
            if (bold) setTypeface(null, Typeface.BOLD)
            parent.addView(this)
        }
    }
    private fun section(title: String, value: String): TextView {
        content.addView(View(context).apply { setBackgroundColor(Color.parseColor("#29404c")) },
            LinearLayout.LayoutParams(-1, dp(1)).apply { topMargin = dp(16); bottomMargin = dp(10) })
        val heading = addText(title, 16f, "#edf5f8", true)
        addText(value)
        return heading
    }
    private fun jumpTo(target: View?) {
        if (target == null) return
        scroll.post {
            if (!target.isAttachedToWindow || target.parent !== content) return@post
            val bounds = Rect(0, 0, target.width, target.height)
            scroll.offsetDescendantRectToMyCoords(target, bounds)
            scroll.smoothScrollTo(0, (bounds.top - dp(8)).coerceAtLeast(0))
        }
    }
    private fun render() {
        val entry = history.last()
        back.text = if (history.size == 1) "Back to references" else "Back to previous reference"
        content.removeAllViews()
        val header = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            background = GradientDrawable().apply {
                setColor(Color.parseColor("#142532")); cornerRadius = dp(16).toFloat()
            }
        }
        content.addView(header, LinearLayout.LayoutParams(-1, -2).apply { bottomMargin = dp(12) })
        addText("${entry.category} · Offline reference", 12f, "#78d8db", true, header)
        addText(entry.title, 22f, "#edf5f8", true, header)
        addText(entry.summary, 14f, "#c1d4df", false, header)
        val destinations = mutableMapOf<String, View>()
        val hasFieldUse = entry.id !in setOf("expanded-dbm-table", "expanded-db-ratio-table", "expanded-cidr-table")
        addText("Jump to", 14f, "#edf5f8", true)
        val shortcuts = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }
        content.addView(shortcuts)
        (listOfNotNull(if (hasFieldUse) "Field use" else null, "What to record", "Limits", "Source")).chunked(2).forEach { names ->
            val row = LinearLayout(context).apply { orientation = LinearLayout.HORIZONTAL }
            shortcuts.addView(row)
            names.forEachIndexed { index, name ->
                row.addView(Button(context).apply {
                    styleFieldButton(); text = name; contentDescription = "Jump to $name"
                    setOnClickListener { jumpTo(destinations[name]) }
                }, LinearLayout.LayoutParams(0, -2, 1f).apply { if (index == 0) marginEnd = dp(6) })
            }
        }
        GuideVisuals.create(context, entry.id)?.let { content.addView(it, LinearLayout.LayoutParams(-1, -2)) }
        ReferenceVisuals.addTo(content, entry.id)
        ReferenceReaderModel.valueReference(entry.id)?.let { section("Values and context", it) }
        ReferenceReaderModel.expanded(entry).forEach { (title, body) -> section(title, body) }
        if (hasFieldUse) {
            destinations["Field use"] = section(if (entry.category == "Guides") "Field workflow" else "How to use this in the field", entry.fieldUse)
        }
        destinations["What to record"] = section("What to record", ReferenceReaderModel.recordPrompt(entry))
        section("Questions to check", ReferenceReaderModel.checks(entry).joinToString("\n\n") { "• $it" })
        destinations["Limits"] = section("Limits and interpretation", entry.limitations)
        destinations["Source"] = section("Source and reference date", "${entry.sourceName}\n${entry.sourceUrl}\nReference record date: ${entry.reviewed}. Source material can change; verify current rules and equipment specifications.")
        if (entry.tags.isNotEmpty()) section("Topics", entry.tags.joinToString(" · "))
        val related = ReferenceReaderModel.related(entry)
        if (related.isNotEmpty()) {
            addText("Related references", 16f, "#edf5f8", true)
            related.forEach { candidate ->
                content.addView(Button(context).apply {
                    styleFieldButton(); text = candidate.title; contentDescription = "Open related reference: ${candidate.title}"
                    setOnClickListener { history.add(candidate); render() }
                }, LinearLayout.LayoutParams(-1, -2).apply { topMargin = dp(4) })
            }
        }
        scroll.post { scroll.scrollTo(0, 0) }
    }
}
