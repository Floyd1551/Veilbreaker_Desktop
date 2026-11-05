package com.veilbreaker.companion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.TypedValue
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.max
import kotlin.math.min

/** A transient schematic line between distinct reported samples; never persisted. */
class LiveCellTrendView(context: Context) : LinearLayout(context) {
    private val title = TextView(context)
    private val description = TextView(context)
    private val graph = TrendGraph(context)
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()
    init {
        orientation = VERTICAL
        title.textSize = 14f; title.setTextColor(Color.parseColor("#63d6ee")); title.setPadding(0, dp(8), 0, dp(3))
        description.textSize = 12f; description.setTextColor(Color.parseColor("#b8cbd9")); description.setPadding(0, dp(3), 0, dp(5))
        val labelPixels = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 10f, resources.displayMetrics)
        val chartHeight = max(dp(150), dp(100) + ceil(labelPixels * 5).toInt())
        addView(title); addView(graph, LayoutParams(LayoutParams.MATCH_PARENT, chartHeight)); addView(description)
    }
    fun show(history: LiveCellTrend) {
        val values = history.points
        title.text = if (history.metric.isEmpty()) "SERVING CELL HISTORY" else "${history.metric} · ${history.cellLabel}"
        description.text = history.status + "\n${values.size} distinct modem timestamp(s); not a continuous measurement. Samples older than 20 s at receipt are excluded."
        graph.show(values, history.metric)
    }

    private class TrendGraph(context: Context) : View(context) {
        private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
        private var points = emptyList<LiveCellTrend.Point>()
        private var metric = ""
        fun show(values: List<LiveCellTrend.Point>, name: String) {
            points = values; metric = name
            contentDescription = if (values.isEmpty()) "No eligible live cellular history." else
                "$name history, ${values.size} distinct modem samples. Latest ${values.last().value} dBm, ${values.last().ageAtReceiptMs} milliseconds old at receipt."
            invalidate()
        }
        override fun onDraw(canvas: Canvas) {
            super.onDraw(canvas)
            canvas.drawColor(Color.rgb(10, 24, 36))
            val density = resources.displayMetrics.density
            paint.style = Paint.Style.FILL
            paint.textSize = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 10f, resources.displayMetrics)
            paint.color = Color.rgb(170, 191, 206)
            val font = paint.fontMetrics
            val textHeight = font.descent - font.ascent
            if (points.isEmpty()) { paint.textAlign = Paint.Align.LEFT; canvas.drawText("No eligible samples", 12f*density, -font.ascent + 8f*density, paint); return }
            val low = max(-160.0, floor((points.minOf { it.value } - 5.0) / 5.0) * 5.0)
            val high = min(-20.0, ceil((points.maxOf { it.value } + 5.0) / 5.0) * 5.0)
            val left = max(43f*density, paint.measureText(low.toInt().toString()) + 10f*density)
            val unitBaseline = -font.ascent + 2f*density
            val right = width - 12f*density
            val top = max(20f*density, unitBaseline + font.descent - font.ascent + 4f*density)
            val bottom = height - max(26f*density, font.descent + textHeight + 8f*density)
            if (right <= left || bottom <= top || high <= low) return
            paint.textAlign = Paint.Align.RIGHT
            canvas.drawText(high.toInt().toString(), left-5f*density, top+4f*density, paint)
            canvas.drawText(low.toInt().toString(), left-5f*density, bottom+4f*density, paint)
            paint.color=Color.rgb(48,69,87); paint.strokeWidth=density
            canvas.drawLine(left,top,right,top,paint); canvas.drawLine(left,bottom,right,bottom,paint)
            val first = points.first().modemElapsedMs
            val span = max(1L, points.last().modemElapsedMs-first)
            var previousX = 0f; var previousY = 0f
            paint.color=Color.rgb(99,222,200); paint.strokeWidth=2f*density
            points.forEachIndexed { index, point ->
                val x = if (points.size == 1) (left+right)/2 else left+((point.modemElapsedMs-first).toDouble()/span*(right-left)).toFloat()
                val y = bottom-((point.value-low)/(high-low)*(bottom-top)).toFloat()
                if (index > 0) canvas.drawLine(previousX,previousY,x,y,paint)
                canvas.drawCircle(x,y,3f*density,paint); previousX=x; previousY=y
            }
            paint.color=Color.rgb(170,191,206); paint.textAlign=Paint.Align.LEFT
            canvas.drawText("dBm",left,unitBaseline,paint)
            paint.textAlign=Paint.Align.RIGHT; canvas.drawText("${if(points.size == 1) 0 else span/1000}s",right,height-font.descent-4f*density,paint)
        }
    }
}
