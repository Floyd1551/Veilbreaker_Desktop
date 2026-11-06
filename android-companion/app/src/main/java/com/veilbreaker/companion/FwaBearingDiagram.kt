package com.veilbreaker.companion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.view.View
import java.util.Locale
import kotlin.math.cos
import kotlin.math.sin

/** Compass-style illustration of the calculated true bearing, not terrain or LOS. */
class FwaBearingDiagram(context: Context) : View(context) {
    private val density = resources.displayMetrics.density
    private val stroke = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#4d7589"); style = Paint.Style.STROKE; strokeWidth = 2f * density }
    private val arrow = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#58d9e5"); strokeWidth = 3f * density; strokeCap = Paint.Cap.ROUND }
    private val label = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#d4e9f0"); textAlign = Paint.Align.CENTER; textSize = 12 * resources.displayMetrics.scaledDensity }
    var trueBearing: Double? = null
        set(value) {
            field = value?.takeIf { it.isFinite() && it >= 0 && it < 360 }
            contentDescription = field?.let { "Schematic true bearing ${String.format(Locale.US, "%.1f", it)} degrees. Not a terrain or line-of-sight assessment." } ?: "No bearing calculated"
            invalidate()
        }
    init { isFocusable = true; importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val bearing = trueBearing ?: return
        canvas.drawColor(Color.parseColor("#0b1b29"))
        val cx = width / 2f; val cy = height / 2f; val r = minOf(width, height) * 0.32f
        canvas.drawCircle(cx, cy, r, stroke)
        val angle = Math.toRadians(bearing)
        val x = cx + (r * sin(angle)).toFloat(); val y = cy - (r * cos(angle)).toFloat()
        canvas.drawLine(cx, cy, x, y, arrow)
        canvas.drawCircle(x, y, 4 * density, arrow)
        canvas.drawText("N", cx, cy - r - 5 * density, label)
        canvas.drawText("S", cx, cy + r + 14 * density, label)
        canvas.drawText("W", cx - r - 12 * density, cy + 4 * density, label)
        canvas.drawText("E", cx + r + 12 * density, cy + 4 * density, label)
    }
}
