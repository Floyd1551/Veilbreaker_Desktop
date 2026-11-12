package com.veilbreaker.companion

import android.app.Dialog
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.ColorDrawable
import android.view.KeyEvent
import android.view.ViewGroup
import android.view.Window
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.util.Locale

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
            setBackgroundColor(Color.parseColor("#07131f"))
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
        window?.setBackgroundDrawable(ColorDrawable(Color.parseColor("#07131f")))
        window?.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
    }

    private fun goBack() {
        if (history.size == 1) dismiss() else { history.removeAt(history.lastIndex); render() }
    }
    private fun addText(value: String, size: Float = 14f, color: String = "#c1d4df", bold: Boolean = false) {
        content.addView(TextView(context).apply {
            text = value; textSize = size; setTextColor(Color.parseColor(color)); setTextIsSelectable(true)
            setPadding(0, dp(5), 0, dp(7)); setLineSpacing(dp(2).toFloat(), 1f)
            if (bold) setTypeface(null, Typeface.BOLD)
        })
    }
    private fun section(title: String, value: String) {
        addText(title.uppercase(Locale.ROOT), 11f, "#63d6ee", true)
        addText(value)
    }
    private fun render() {
        val entry = history.last()
        back.text = if (history.size == 1) "Back to references" else "Back to previous reference"
        content.removeAllViews()
        addText(entry.category.uppercase(Locale.ROOT) + " · OFFLINE REFERENCE", 11f, "#63d6ee", true)
        addText(entry.title, 22f, "#f2f8fc", true)
        section("Overview", entry.summary)
        GuideVisuals.create(context, entry.id)?.let { content.addView(it, LinearLayout.LayoutParams(-1, -2)) }
        ReferenceVisuals.addTo(content, entry.id)
        ReferenceReaderModel.valueReference(entry.id)?.let { section("Values and context", it) }
        ReferenceReaderModel.expanded(entry).forEach { (title, body) -> section(title, body) }
        if (entry.id !in setOf("expanded-dbm-table", "expanded-db-ratio-table", "expanded-cidr-table")) {
            section(if (entry.category == "Guides") "Field workflow" else "How to use this in the field", entry.fieldUse)
        }
        section("What to record", ReferenceReaderModel.recordPrompt(entry))
        section("Questions to check", ReferenceReaderModel.checks(entry).joinToString("\n\n") { "• $it" })
        section("Limits and interpretation", entry.limitations)
        section("Source and reference date", "${entry.sourceName}\n${entry.sourceUrl}\nReference record date: ${entry.reviewed}. Source material can change; verify current rules and equipment specifications.")
        if (entry.tags.isNotEmpty()) section("Topics", entry.tags.joinToString(" · "))
        val related = ReferenceReaderModel.related(entry)
        if (related.isNotEmpty()) {
            addText("RELATED REFERENCES", 11f, "#63d6ee", true)
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
