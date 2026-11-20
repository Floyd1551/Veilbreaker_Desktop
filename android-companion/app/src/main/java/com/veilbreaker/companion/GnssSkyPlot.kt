package com.veilbreaker.companion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.util.TypedValue
import android.view.View
import kotlin.math.max
import kotlin.math.min

/** Schematic polar plot of Android-reported satellite angles; never persists measurements. */
internal class GnssSkyPlot(context: Context) : View(context) {
    private val ink = Paint(Paint.ANTI_ALIAS_FLAG)
    private var points: List<GnssSkyModel.Point> = emptyList()

    init { importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO }

    fun show(frame: GnssSkyModel.Frame) {
        points = if (frame.state == GnssSkyModel.State.READY) frame.points else emptyList()
        invalidate()
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val density = resources.displayMetrics.density
        setMeasuredDimension(MeasureSpec.getSize(widthMeasureSpec), resolveSize((220 * density).toInt(), heightMeasureSpec))
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (points.isEmpty()) return
        val density = resources.displayMetrics.density
        val cx = width / 2f; val cy = height / 2f
        ink.textSize = TypedValue.applyDimension(TypedValue.COMPLEX_UNIT_SP, 11f, resources.displayMetrics)
        val halfLabel = max((ink.fontMetrics.descent - ink.fontMetrics.ascent) / 2f, ink.measureText("W") / 2f)
        val radius = min(width, height) / 2f - 2f * halfLabel - 8f * density
        if (radius <= 0f) return
        ink.style = Paint.Style.STROKE; ink.strokeWidth = density; ink.color = Color.parseColor("#395064")
        for (fraction in floatArrayOf(1f, 2f / 3f, 1f / 3f)) canvas.drawCircle(cx, cy, radius * fraction, ink)
        canvas.drawLine(cx - radius, cy, cx + radius, cy, ink)
        canvas.drawLine(cx, cy - radius, cx, cy + radius, ink)
        ink.style = Paint.Style.FILL; ink.textAlign = Paint.Align.CENTER
        ink.color = Color.parseColor("#a9bfce")
        val baseline = (ink.fontMetrics.ascent + ink.fontMetrics.descent) / 2f
        val offset = radius + halfLabel + 4f * density
        canvas.drawText("N", cx, cy - offset - baseline, ink)
        canvas.drawText("E", cx + offset, cy - baseline, ink)
        canvas.drawText("S", cx, cy + offset - baseline, ink)
        canvas.drawText("W", cx - offset, cy - baseline, ink)
        for (point in points) {
            val x = cx + (point.x * radius).toFloat(); val y = cy + (point.y * radius).toFloat()
            ink.style = if (point.used) Paint.Style.FILL else Paint.Style.STROKE
            ink.strokeWidth = 2f * density
            ink.color = Color.parseColor(if (point.used) "#63dec8" else "#f1b865")
            canvas.drawCircle(x, y, 4f * density, ink)
        }
    }
}
