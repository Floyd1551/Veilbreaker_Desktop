package com.veilbreaker.companion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONObject
import java.util.Locale
import kotlin.math.max
import kotlin.math.min

private const val TEXT = "#e5edf5"
private const val MUTED = "#a9bfce"
private const val CYAN = "#63dec8"
private fun Context.dp(value: Int) = (value * resources.displayMetrics.density).toInt()
private fun number(value: Double): String = if (value == value.toLong().toDouble()) value.toLong().toString() else String.format(Locale.US,"%.1f",value)

/** The graphic has no embedded text; labels remain scalable Android text views. */
private class GaugeGraphic(context: Context, private val metric: CellularDashboard.Metric, private val stacked: Boolean) : View(context) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG)
    init {
        importantForAccessibility=IMPORTANT_FOR_ACCESSIBILITY_NO
    }
    override fun onMeasure(widthMeasureSpec: Int,heightMeasureSpec: Int) {
        setMeasuredDimension(MeasureSpec.getSize(widthMeasureSpec),resolveSize(context.dp(if(stacked) 16 else 70),heightMeasureSpec))
    }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val density=resources.displayMetrics.density
        paint.style=Paint.Style.STROKE;paint.strokeWidth=6*density;paint.strokeCap=Paint.Cap.ROUND
        val fraction=metric.value?.let { ((it-metric.low)/(metric.high-metric.low)).coerceIn(0.0,1.0).toFloat() }
        if(stacked) {
            val left=4*density; val right=max(left,width-4*density); val y=height/2f
            paint.color=Color.parseColor("#304557");canvas.drawLine(left,y,right,y,paint)
            if(fraction != null) { paint.color=Color.parseColor(CYAN);canvas.drawLine(left,y,left+(right-left)*fraction,y,paint) }
        } else {
            val cx=width/2f; val radius=min(width*0.34f, context.dp(30).toFloat()); val cy=height/2f
            val rect=RectF(cx-radius,cy-radius,cx+radius,cy+radius)
            paint.color=Color.parseColor("#304557");canvas.drawArc(rect,135f,270f,false,paint)
            if(fraction != null) { paint.color=Color.parseColor(CYAN);canvas.drawArc(rect,135f,fraction*270f,false,paint) }
        }
    }
}

/** One bounded visual scale, explicitly not a universal service-quality score. */
private class CellularGauge(context: Context, metric: CellularDashboard.Metric, stacked: Boolean) : LinearLayout(context) {
    init {
        orientation=VERTICAL
        val shown=metric.value?.let { "${number(it)} ${metric.unit}" } ?: "Not exposed"
        contentDescription="${metric.name}: $shown. Display scale ${metric.low.toInt()} to ${metric.high.toInt()} ${metric.unit}."
        importantForAccessibility=IMPORTANT_FOR_ACCESSIBILITY_YES
        val align=if(stacked) Gravity.START else Gravity.CENTER
        fun text(value: String, size: Float, bold: Boolean): TextView = TextView(context).apply {
            this.text=value;textSize=size;gravity=align
            setTextColor(Color.parseColor(if(bold) TEXT else MUTED))
            if(bold)setTypeface(null,Typeface.BOLD)
            importantForAccessibility=IMPORTANT_FOR_ACCESSIBILITY_NO
        }
        addView(text(metric.name,13f,false),LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT))
        addView(text(shown,16f,true),LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT))
        addView(GaugeGraphic(context,metric,stacked),LayoutParams(LayoutParams.MATCH_PARENT,context.dp(if(stacked) 16 else 70)))
        if(stacked)setPadding(0,context.dp(6),0,context.dp(6))
    }
}

/** Plot distinct modem-receipt timestamps from one identified cell, not a live history. */
private class CellularTrend(context: Context, private val points: List<CellularDashboard.Point>) : View(context) {
    private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
    init { contentDescription="Signal history: ${points.size} distinct modem-receipt timestamps from the selected captured cell."; importantForAccessibility=IMPORTANT_FOR_ACCESSIBILITY_YES }
    override fun onMeasure(widthMeasureSpec:Int,heightMeasureSpec:Int) {
        val scale=resources.configuration.fontScale.takeIf { it.isFinite() && it>1f } ?: 1f
        val height=context.dp((130+50*(scale-1)).toInt())
        setMeasuredDimension(MeasureSpec.getSize(widthMeasureSpec),resolveSize(height,heightMeasureSpec))
    }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if(points.size < 2) return
        val density=resources.displayMetrics.density; val scaled=resources.displayMetrics.scaledDensity
        val low=min(-140.0,points.minOf { it.value });val high=max(-60.0,points.maxOf { it.value })
        val first=points.first().elapsedMs;val span=max(1L,points.last().elapsedMs-first)
        paint.textSize=10*scaled;paint.textAlign=Paint.Align.RIGHT;paint.style=Paint.Style.FILL;paint.color=Color.parseColor(MUTED)
        val font=paint.fontMetrics
        val left=max(context.dp(45).toFloat(),max(paint.measureText(number(high)),paint.measureText(number(low)))+context.dp(8))
        val right=max(left+1,width-context.dp(12).toFloat())
        val top=-font.ascent+context.dp(4)
        val bottom=max(top+1,height-(font.descent-font.ascent)-context.dp(12))
        canvas.drawText("${number(high)}",left-5*density,top+4*density,paint);canvas.drawText("${number(low)}",left-5*density,bottom+4*density,paint)
        paint.color=Color.parseColor("#304557");paint.strokeWidth=density
        canvas.drawLine(left,top,right,top,paint);canvas.drawLine(left,bottom,right,bottom,paint)
        paint.color=Color.parseColor(CYAN);paint.strokeWidth=2*density
        var lastX=0f;var lastY=0f
        for ((i,p) in points.withIndex()) {
            val x=left+((p.elapsedMs-first).toDouble()/span*(right-left)).toFloat()
            val y=bottom-((p.value-low)/(high-low)*(bottom-top)).toFloat()
            if(i>0) canvas.drawLine(lastX,lastY,x,y,paint)
            canvas.drawCircle(x,y,2.5f*density,paint);lastX=x;lastY=y
        }
        paint.color=Color.parseColor(MUTED);paint.textAlign=Paint.Align.RIGHT
        canvas.drawText("${span / 1000}s",right,height-font.descent-context.dp(2),paint)
    }
}

/** Reusable panel in the existing capture flow. It reads only saved evidence. */
class CellularVisuals(context: Context) : LinearLayout(context) {
    init { orientation=VERTICAL }
    private fun label(value:String,size:Float=13f,strong:Boolean=false): TextView = TextView(context).apply {
        text=value;textSize=size;setTextColor(Color.parseColor(if(strong) TEXT else MUTED));
        if(strong)setTypeface(null,Typeface.BOLD);setPadding(0,context.dp(3),0,context.dp(5));this@CellularVisuals.addView(this)
    }
    fun showCapture(capture: JSONObject?, plan: JSONObject?) {
        removeAllViews()
        label("CELLULAR OVERVIEW",15f,true)
        if(capture==null) { label("Capture cellular data to see signal gauges and a measured trend.");return }
        val cards=runCatching { CellularDashboard.build(capture,plan) }.getOrElse { emptyList() }
        label("Last saved capture · values and sample ages are at receipt, not live.")
        if(cards.isEmpty()) { label("No registered LTE or NR cell reported. Missing data remains unknown.");return }
        for(card in cards.take(8)) {
            val content=LinearLayout(context).apply {
                orientation=VERTICAL;setPadding(context.dp(12),context.dp(8),context.dp(12),context.dp(10))
                background=GradientDrawable().apply { setColor(Color.parseColor("#101c2a"));cornerRadius=context.dp(10).toFloat() }
            }
            addView(content,LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT).apply { topMargin=context.dp(8) })
            fun detail(value:String,strong:Boolean=false) { content.addView(TextView(context).apply {
                text=value;textSize=if(strong) 14f else 12f;setTextColor(Color.parseColor(if(strong) TEXT else MUTED));
                if(strong)setTypeface(null,Typeface.BOLD);setPadding(0,context.dp(3),0,context.dp(3)) }) }
            detail(card.context,true);detail("Received ${card.receivedUtc} · ${card.age}")
            val configuration=resources.configuration
            val stacked=CellularGaugeLayout.stacked(configuration.screenWidthDp,configuration.fontScale)
            val gauges=LinearLayout(context).apply { orientation=if(stacked) VERTICAL else HORIZONTAL }
            card.metrics.forEach {
                val params=if(stacked) LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT)
                           else LayoutParams(0,LayoutParams.WRAP_CONTENT,1f)
                gauges.addView(CellularGauge(context,it,stacked),params)
            }
            content.addView(gauges)
            detail("Gauge scales are reference ranges; values outside them are shown in full.")
            if(card.trend.size>=2) {
                detail("${card.metrics[0].name} · ${card.trend.size} distinct modem-receipt timestamps",true)
                content.addView(CellularTrend(context,card.trend),LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT))
                detail("Saved observations connected for readability; intervals are not continuous measurements.")
            } else detail("Trend needs at least two distinct timed observations from the same identified cell.")
        }
        if(cards.size>8) label("Showing 8 registered cells; see capture details for the complete list.")
    }
}
