package com.veilbreaker.companion

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView

/** A compact visual field workflow and cue table; no remote assets or measured claims. */
object GuideVisuals {
    fun create(context: Context, entryId: String): View? {
        val guide = GuideVisualsCatalog.forEntry(entryId) ?: return null
        fun dp(value: Int) = (value * context.resources.displayMetrics.density).toInt()
        fun label(value: String, size: Float, color: String, bold: Boolean = false) = TextView(context).apply {
            text = value; textSize = size; setTextColor(Color.parseColor(color)); if (bold) setTypeface(null, Typeface.BOLD)
        }
        val panel = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL; setPadding(dp(12), dp(10), dp(12), dp(12))
            background = GradientDrawable().apply { setColor(Color.parseColor("#0b1b29")); setStroke(dp(1), Color.parseColor("#29495a")); cornerRadius = dp(9).toFloat() }
        }
        panel.addView(label("FIELD WORKFLOW · SCHEMATIC", 12f, "#72d9e8", true))
        panel.addView(label("Guidance for investigation; not a measured result.", 12f, "#b8cbd9").apply { setPadding(0, dp(4), 0, dp(8)) })
        guide.stages.forEachIndexed { index, stage ->
            val row = LinearLayout(context).apply { orientation = LinearLayout.HORIZONTAL; gravity = Gravity.TOP }
            val marker = label((index + 1).toString(), 13f, "#09232d", true).apply {
                gravity = Gravity.CENTER; importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
                background = GradientDrawable().apply { setColor(Color.parseColor("#66d7e3")); shape = GradientDrawable.OVAL }
            }
            row.addView(marker, LinearLayout.LayoutParams(dp(28), dp(28)).apply { marginEnd = dp(10) })
            val detail = LinearLayout(context).apply { orientation = LinearLayout.VERTICAL }
            detail.addView(label(stage.title, 12f, "#e8f5fa", true).apply { contentDescription = "Step ${index + 1}: ${stage.title}" })
            detail.addView(label(stage.detail, 13f, "#b8cbd9").apply { setPadding(0, dp(2), 0, dp(7)) })
            row.addView(detail, LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            panel.addView(row)
            if (index < guide.stages.lastIndex) {
                panel.addView(label("│", 14f, "#54899c").apply {
                    gravity = Gravity.CENTER; importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
                }, LinearLayout.LayoutParams(dp(28), LinearLayout.LayoutParams.WRAP_CONTENT))
            }
        }
        panel.addView(label("DECISION CUES", 12f, "#72d9e8", true).apply { setPadding(0, dp(8), 0, dp(5)) })
        fun cell(value: String, heading: Boolean): TextView = label(value, if (heading) 11f else 12f,
            if (heading) "#9dc5d6" else "#e1eef5", heading).apply { setPadding(dp(6), dp(6), dp(6), dp(6)) }
        fun tableRow(left: String, right: String, heading: Boolean) {
            val row = LinearLayout(context).apply {
                orientation = LinearLayout.HORIZONTAL
                setBackgroundColor(Color.parseColor(if (heading) "#183346" else "#102738"))
            }
            row.addView(cell(left, heading), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f))
            row.addView(cell(right, heading), LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1.3f))
            panel.addView(row, LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(1) })
        }
        tableRow("Observation", "Check next", true)
        guide.cues.forEach { tableRow(it.observation, it.nextStep, false) }
        panel.addView(label("Cues suggest checks; they do not establish a cause.", 11f, "#9db9c9").apply { setPadding(0, dp(7), 0, 0) })
        return panel
    }
}
