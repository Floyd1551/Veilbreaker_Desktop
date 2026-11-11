package com.veilbreaker.companion

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale

/** Compact, numeric view of one transient Android-reported serving-cell response. */
class LiveCellMetricsPanel(context: Context) : LinearLayout(context) {
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    init { orientation = VERTICAL }

    private fun label(parent: LinearLayout, value: String, size: Float, bold: Boolean = false) = TextView(context).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(if (bold) "#f2f8fc" else "#b8cbd9"))
        if (bold) setTypeface(null, Typeface.BOLD)
        setPadding(0, dp(3), 0, dp(3)); parent.addView(this)
    }

    fun show(card: LiveOverviewModel.Cell?) {
        removeAllViews()
        if (card == null) {
            label(this, "No unambiguous LTE/NR serving cell was reported in this response. See cell reports below.", 13f)
            return
        }
        label(this, card.title, 15f, true)
        label(this, "${card.carrier} · ${card.band}\nChannel ${card.channel} · PCI ${card.pci}\n${card.age}", 12f)
        val row = LinearLayout(context).apply {
            orientation = if (resources.configuration.screenWidthDp < 360 || resources.configuration.fontScale > 1.15f) VERTICAL else HORIZONTAL
            this@LiveCellMetricsPanel.addView(this)
        }
        card.values.forEach { value ->
            val box = LinearLayout(context).apply {
                orientation = VERTICAL; setPadding(dp(8), dp(6), dp(8), dp(6))
                background = GradientDrawable().apply { setColor(Color.parseColor("#102638")); setStroke(dp(1), Color.parseColor("#29495a")); cornerRadius = dp(6).toFloat() }
                row.addView(this, if (row.orientation == HORIZONTAL) LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f).apply { marginEnd = dp(4) }
                    else LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT).apply { bottomMargin = dp(4) })
            }
            label(box, value.label, 12f)
            val number = value.value?.let { if (it == it.toLong().toDouble()) it.toLong().toString() else String.format(Locale.US, "%.1f", it) }
            label(box, if (number == null) "Unavailable" else "$number ${value.unit}", 16f, true)
        }
    }
}
