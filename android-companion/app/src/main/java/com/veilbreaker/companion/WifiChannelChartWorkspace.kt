package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale

/** Read-only chart of Android's cached scan observations; never initiates a scan. */
class WifiChannelChartWorkspace(context: Context, samples: List<WifiChannelPlotModel.Sample>) : LinearLayout(context) {
    private val points = WifiChannelPlotModel.aggregate(samples)
    private val bandButtons = mutableListOf<Button>()
    private val detail = TextView(context)
    private val plot = ChannelPlot(context)
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    private fun label(value: String, size: Float, accent: Boolean = false) = TextView(context).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(if (accent) "#63dec8" else "#b8c9da"))
        setPadding(0, dp(4), 0, dp(4)); if (accent) setTypeface(null, Typeface.BOLD)
    }

    init {
        orientation = VERTICAL; setPadding(dp(12), dp(10), dp(12), dp(12))
        background = GradientDrawable().apply { setColor(Color.parseColor("#152435")); cornerRadius = dp(12).toFloat(); setStroke(dp(1), Color.parseColor("#294055")) }
        addView(label("CACHED WI-FI BY FREQUENCY", 12f, true))
        addView(label("Strongest reported RSSI at each primary center frequency. Numbers show cached observations at that frequency, not channel widths or measured utilization.", 12f))
        val tabs = LinearLayout(context).apply { orientation = HORIZONTAL; gravity = Gravity.CENTER_VERTICAL }
        WifiChannelPlotModel.Band.entries.forEach { band ->
            val button = Button(context).apply {
                text = band.title; textSize = 12f; isAllCaps = false; minHeight = dp(48); contentDescription = "Show cached ${band.title} Wi-Fi observations"
                setTextColor(Color.WHITE); setOnClickListener { showBand(band) }
            }
            tabs.addView(button, LayoutParams(0, LayoutParams.WRAP_CONTENT, 1f)); bandButtons.add(button)
        }
        addView(tabs)
        addView(plot, LayoutParams(LayoutParams.MATCH_PARENT, dp(220)))
        addView(label("RSSI display range −100 to −30 dBm; values outside the scale are clipped. No channel width, coverage or interference is inferred.", 11f))
        detail.textSize = 12f; detail.setTextColor(Color.parseColor("#b8c9da")); detail.setTextIsSelectable(true); addView(detail)
        showBand(WifiChannelPlotModel.Band.GHZ_24)
    }

    private fun showBand(band: WifiChannelPlotModel.Band) {
        bandButtons.forEachIndexed { index, button ->
            val selected = WifiChannelPlotModel.Band.entries[index] == band
            button.backgroundTintList = ColorStateList.valueOf(Color.parseColor(if (selected) "#2179ce" else "#243b50"))
            button.isSelected = selected
        }
        val selected = points.filter { it.band == band }
        plot.show(band, selected)
        detail.text = if (selected.isEmpty()) "No valid cached ${band.title} observations. This does not mean the band is empty." else {
            val lines = mutableListOf("${selected.sumOf { it.observationCount }} cached observations at ${selected.size} frequencies; ages are at the time the cached list was read.")
            selected.take(20).forEach { point ->
                val age = when {
                    point.youngestSeconds == null -> "age unavailable"
                    point.youngestSeconds == point.oldestSeconds -> "${point.youngestSeconds}s old"
                    else -> "${point.youngestSeconds}–${point.oldestSeconds}s old"
                }
                val unknown = if (point.ageUnavailableCount > 0 && point.youngestSeconds != null) "; ${point.ageUnavailableCount} age unavailable" else ""
                lines.add("${point.frequencyMhz} MHz · strongest ${point.strongestDbm} dBm · ${point.observationCount} cached · $age$unknown")
            }
            if (selected.size > 20) lines.add("Additional frequencies are shown on the chart; list limited to 20.")
            lines.joinToString("\n")
        }
    }

    /** Plot points are frequencies only; channel spans and transmitter identity are not inferred. */
    private class ChannelPlot(context: Context) : View(context) {
        private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        private var band = WifiChannelPlotModel.Band.GHZ_24
        private var points: List<WifiChannelPlotModel.Point> = emptyList()
        private val density get() = resources.displayMetrics.density
        fun show(selected: WifiChannelPlotModel.Band, values: List<WifiChannelPlotModel.Point>) {
            band = selected; points = values
            contentDescription = "${band.title} cached Wi-Fi signal by reported frequency; details follow the chart."
            invalidate()
        }
        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            canvas.drawColor(Color.rgb(10, 24, 36))
            val left = 42f*density; val right = width - 14f*density
            val top = 20f*density; val bottom = height - 28f*density
            if (right <= left || bottom <= top) return
            paint.typeface = Typeface.DEFAULT; paint.textSize = 10f*resources.displayMetrics.scaledDensity; paint.strokeWidth = density
            for (value in listOf(-100, -80, -60, -40, -30)) {
                val y = top + (-30f - value)/70f*(bottom-top)
                paint.color = Color.rgb(46, 67, 82); canvas.drawLine(left, y, right, y, paint)
                paint.textAlign = Paint.Align.RIGHT; paint.color = Color.rgb(170, 191, 206)
                canvas.drawText(value.toString(), left-5f*density, y+3f*density, paint)
            }
            paint.color = Color.rgb(170, 191, 206); paint.textAlign = Paint.Align.LEFT
            canvas.drawText("dBm", left, 12f*density, paint)
            canvas.drawText("${band.minMhz}", left, height-8f*density, paint)
            paint.textAlign = Paint.Align.RIGHT; canvas.drawText("${band.maxMhz} MHz", right, height-8f*density, paint)
            for (point in points) {
                val x = left+(point.frequencyMhz-band.minMhz).toFloat()/(band.maxMhz-band.minMhz)*(right-left)
                val y = top+(-30f-point.strongestDbm.coerceIn(-100,-30))/70f*(bottom-top)
                paint.style = Paint.Style.FILL; paint.color = Color.rgb(89, 220, 201)
                canvas.drawCircle(x, y, 4f*density, paint)
                if (point.observationCount > 1) {
                    paint.textAlign = Paint.Align.CENTER; paint.color = Color.WHITE; paint.textSize = 10f*resources.displayMetrics.scaledDensity
                    canvas.drawText(String.format(Locale.US, "%d", point.observationCount), x, (y-6f*density).coerceAtLeast(top+10f*density), paint)
                }
            }
        }
    }
}
