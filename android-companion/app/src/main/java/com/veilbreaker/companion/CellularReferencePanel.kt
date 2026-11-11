package com.veilbreaker.companion

import android.content.Context
import android.graphics.Color
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/** Shared offline explanations; reference guidance is not captured evidence. */
class CellularReferencePanel(context: Context) : LinearLayout(context) {
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()

    init {
        orientation = VERTICAL
        val reference = TextView(context).apply {
            textSize = 13f; setTextColor(Color.parseColor("#e8f5fa")); setTextIsSelectable(true)
            setPadding(dp(8), dp(6), dp(8), dp(10)); visibility = View.GONE
            text = WirelessReferenceLibrary.entries.filter { it.id in setOf("cell-power", "cell-quality") }
                .joinToString("\n\n") { entry ->
                    "${entry.title}\n${entry.summary}\n\nField use: ${entry.fieldUse}\n\nLimitations: ${entry.limitations}\n\nSource: ${entry.sourceName} · Reviewed ${entry.reviewed}\n${entry.sourceUrl}"
                }
        }
        addView(Button(context).apply {
            text = "Explain cellular measurements"; isAllCaps = false; minHeight = dp(48)
            setOnClickListener {
                val opening = reference.visibility != View.VISIBLE
                reference.visibility = if (opening) View.VISIBLE else View.GONE
                text = if (opening) "Hide measurement explanations" else "Explain cellular measurements"
                isSelected = opening
            }
        })
        addView(reference)
    }
}
