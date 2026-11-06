package com.veilbreaker.companion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.graphics.Typeface
import android.text.TextPaint
import android.text.TextUtils
import android.view.View
import java.util.Locale
import kotlin.math.min

/** Equivalent square and one ideal circle, drawn at a common scale; never an AP placement map. */
internal class WifiPlanningDiagram(context: Context) : View(context) {
    private fun dp(value: Int) = value * resources.displayMetrics.density
    private fun sp(value: Int) = value * resources.displayMetrics.scaledDensity
    private val panel = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#0b1b29") }
    private val border = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#29495a"); style = Paint.Style.STROKE; strokeWidth = dp(1)
    }
    private val square = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#68c3e0"); style = Paint.Style.STROKE; strokeWidth = dp(2)
    }
    private val footprint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#63d9c7"); style = Paint.Style.STROKE; strokeWidth = dp(2)
    }
    private val caption = TextPaint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.parseColor("#bed0dd"); textAlign = Paint.Align.CENTER
    }
    private var shapes: WifiPlanningGeometry.Shapes? = null

    init { importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES }

    /** Called only after a valid calculation; returns false if dimensions cannot be represented. */
    fun showEstimate(areaM2: Double, radiusM: Double, estimate: PlanningModels.Wifi): Boolean {
        val geometry = WifiPlanningGeometry.fromInputs(areaM2, radiusM) ?: run { clearEstimate(); return false }
        shapes = geometry
        contentDescription = String.format(Locale.US,
            "Conceptual geometry, not a coverage map. Entered floor area %.3g square meters, equivalent square compared at the same scale with one assumed AP footprint of radius %.3g meters. Ideal area estimate %d APs; capacity estimate %d APs. No AP locations are shown.",
            areaM2, radiusM, estimate.areaCount, estimate.capacityCount)
        invalidate()
        return true
    }

    fun clearEstimate() { shapes = null; contentDescription = null; invalidate() }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val desiredHeight = (dp(145) + sp(55)).toInt()
        setMeasuredDimension(resolveSize(dp(280).toInt(), widthMeasureSpec), resolveSize(desiredHeight, heightMeasureSpec))
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val value = shapes ?: return
        if (width <= 0 || height <= 0) return
        val margin = dp(2)
        val rect = RectF(margin, margin, width - margin, height - margin)
        canvas.drawRoundRect(rect, dp(8), dp(8), panel)
        canvas.drawRoundRect(rect, dp(8), dp(8), border)

        caption.typeface = Typeface.DEFAULT_BOLD; caption.textSize = sp(11)
        caption.color = Color.parseColor("#75d6e5")
        val titleBaseline = dp(10) + caption.textSize
        drawCentered(canvas, "SCHEMATIC · NOT COVERAGE", width / 2f, titleBaseline, width - dp(20))
        caption.typeface = Typeface.DEFAULT; caption.textSize = sp(10); caption.color = Color.parseColor("#9db9c9")
        val detailBaseline = titleBaseline + dp(4) + caption.textSize
        drawCentered(canvas, "Same scale · no AP locations", width / 2f, detailBaseline, width - dp(20))

        val headerBottom = detailBaseline + dp(8)
        val labelArea = sp(30) + dp(20)
        val availableHeight = (height - headerBottom - labelArea).coerceAtLeast(0f)
        val usableDiameter = min(width / 2f - dp(32), availableHeight - dp(8)).coerceAtLeast(0f)
        val cy = headerBottom + availableHeight / 2f
        val floorCenter = width * 0.25f; val apCenter = width * 0.75f
        val floorHalf = (usableDiameter * value.floorSideFraction / 2.0).toFloat()
        val apRadius = (usableDiameter * value.apDiameterFraction / 2.0).toFloat()
        canvas.drawRect(floorCenter - floorHalf, cy - floorHalf, floorCenter + floorHalf, cy + floorHalf, square)
        canvas.drawCircle(apCenter, cy, apRadius, footprint)

        caption.typeface = Typeface.DEFAULT; caption.textSize = sp(11)
        caption.color = Color.parseColor("#d9ebf4")
        val labelY = height - dp(12) - caption.textSize
        val labelWidth = width / 2f - dp(12)
        drawCentered(canvas, "Floor", floorCenter, labelY, labelWidth)
        drawCentered(canvas, "One AP", apCenter, labelY, labelWidth)
        caption.color = Color.parseColor("#9db9c9"); caption.textSize = sp(10)
        drawCentered(canvas, "Equivalent square", floorCenter, height - dp(9), labelWidth)
        drawCentered(canvas, "Assumed circle", apCenter, height - dp(9), labelWidth)
    }

    private fun drawCentered(canvas: Canvas, value: String, x: Float, y: Float, maxWidth: Float) {
        val label = TextUtils.ellipsize(value, caption, maxWidth.coerceAtLeast(0f), TextUtils.TruncateAt.END)
        canvas.drawText(label, 0, label.length, x, y, caption)
    }
}
