package com.veilbreaker.companion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.graphics.Typeface
import android.view.View
import kotlin.math.sin

/** Reusable illustrative figures. Input positions are shown only after a valid calculation. */
internal class EngineeringToolDiagram(context: Context, private val id: String, private val spec: ToolVisualModel.Spec) : View(context) {
    private fun dp(value: Int) = value * resources.displayMetrics.density
    private fun sp(value: Int) = value * resources.displayMetrics.scaledDensity
    private val panel = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#0b1b29") }
    private val border = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#29495a"); style = Paint.Style.STROKE; strokeWidth = dp(1) }
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#76cce0"); style = Paint.Style.STROKE; strokeWidth = dp(2); strokeCap = Paint.Cap.ROUND }
    private val accent = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#64dccb"); style = Paint.Style.STROKE; strokeWidth = dp(2); strokeCap = Paint.Cap.ROUND }
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#193d50") }
    private val textPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#dcecf4"); textAlign = Paint.Align.CENTER; typeface = Typeface.DEFAULT_BOLD; textSize = sp(11) }
    private var marker: Float? = null

    init { isFocusable = true; importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES; updateAccessibility() }

    fun clearCalculation() { marker = null; updateAccessibility(); invalidate() }

    fun showCalculation(inputs: List<Double>) {
        marker = when (id) {
            "fresnel" -> if (inputs.size >= 3) ToolVisualModel.pathFraction(inputs[1], inputs[2]) else null
            "bulge" -> if (inputs.size >= 2) ToolVisualModel.pathFraction(inputs[0], inputs[1]) else null
            else -> null
        }
        updateAccessibility(); invalidate()
    }

    private fun updateAccessibility() {
        val detail = marker?.let { " The evaluation point is at ${kotlin.math.round(it * 100).toInt()} percent of the path from A." }.orEmpty()
        contentDescription = "Schematic illustration, not to scale. ${spec.description}$detail"
    }

    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        setMeasuredDimension(resolveSize(dp(280).toInt(), widthMeasureSpec), resolveSize((dp(130) + sp(20)).toInt(), heightMeasureSpec))
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (width <= dp(50) || height <= dp(60)) return
        val rect = RectF(dp(1), dp(1), width - dp(1), height - dp(1))
        canvas.drawRoundRect(rect, dp(8), dp(8), panel); canvas.drawRoundRect(rect, dp(8), dp(8), border)
        textPaint.color = Color.parseColor("#75d6e5"); textPaint.textSize = sp(10)
        canvas.drawText("SCHEMATIC · NOT TO SCALE", width / 2f, dp(12) + textPaint.textSize, textPaint)
        textPaint.textSize = sp(11); textPaint.color = Color.parseColor("#dcecf4")
        when (spec.kind) {
            ToolVisualModel.Kind.FRESNEL -> drawFresnel(canvas)
            ToolVisualModel.Kind.EARTH -> drawEarth(canvas)
            ToolVisualModel.Kind.RF_PATH -> drawPath(canvas)
            ToolVisualModel.Kind.CHAIN -> drawStages(canvas, "TX", "+ GAIN", "− LOSS", "RX")
            ToolVisualModel.Kind.OPTICAL -> drawStages(canvas, "OPTICAL TX", "FIBER", "OPTICAL RX")
            ToolVisualModel.Kind.POWER -> drawStages(canvas, "SOURCE", "PATH", "LOAD")
            ToolVisualModel.Kind.NETWORK -> drawStages(canvas, "SOURCE", "LINK", "DEST")
            ToolVisualModel.Kind.WAVE -> drawWave(canvas)
            ToolVisualModel.Kind.REFLECTION -> drawReflection(canvas)
            ToolVisualModel.Kind.NOISE -> drawNoise(canvas)
            ToolVisualModel.Kind.WIFI_RASTER -> drawWifiRaster(canvas)
        }
    }

    private fun bounds(): Pair<Float, Float> = dp(30) to (width - dp(30))
    private fun baseline(): Float = height * 0.55f
    private fun endpointLabels(canvas: Canvas, left: Float, right: Float, y: Float) {
        canvas.drawText("A", left, y + dp(20), textPaint); canvas.drawText("B", right, y + dp(20), textPaint)
    }

    private fun drawFresnel(canvas: Canvas) {
        val (left, right) = bounds(); val y = baseline(); val h = dp(28)
        canvas.drawLine(left, y, right, y, line)
        val upper = Path().apply { moveTo(left, y); quadTo((left + right) / 2, y - 2 * h, right, y) }
        val lower = Path().apply { moveTo(left, y); quadTo((left + right) / 2, y + 2 * h, right, y) }
        canvas.drawPath(upper, accent); canvas.drawPath(lower, accent)
        marker?.let { fraction ->
            val x = left + (right - left) * fraction
            val radius = 4 * h * fraction * (1 - fraction)
            canvas.drawLine(x, y, x, y - radius, line)
            canvas.drawText("r₁", x, y - radius - dp(4), textPaint)
        }
        endpointLabels(canvas, left, right, y + h)
    }

    private fun drawEarth(canvas: Canvas) {
        val (left, right) = bounds(); val y = baseline() - dp(12); val h = dp(35)
        canvas.drawLine(left, y, right, y, line)
        val earth = Path().apply { moveTo(left, y + h); quadTo((left + right) / 2, y - h / 2, right, y + h) }
        canvas.drawPath(earth, accent)
        marker?.let { fraction ->
            val x = left + (right - left) * fraction
            val curve = y + h - 3 * h * fraction * (1 - fraction)
            canvas.drawLine(x, y + h, x, curve, line)
        }
        endpointLabels(canvas, left, right, y + h)
    }

    private fun drawPath(canvas: Canvas) {
        val (left, right) = bounds(); val y = baseline()
        canvas.drawCircle(left, y, dp(5), accent); canvas.drawCircle(right, y, dp(5), accent)
        canvas.drawLine(left + dp(8), y, right - dp(8), y, line)
        canvas.drawLine(right - dp(17), y - dp(6), right - dp(8), y, line)
        canvas.drawLine(right - dp(17), y + dp(6), right - dp(8), y, line)
        canvas.drawText("Ideal free-space path", (left + right) / 2, y - dp(12), textPaint)
        endpointLabels(canvas, left, right, y)
    }

    private fun drawStages(canvas: Canvas, vararg stages: String) {
        val (left, right) = bounds(); val y = baseline(); val gap = dp(8)
        val stageWidth = ((right - left - gap * (stages.size - 1)) / stages.size).coerceAtLeast(dp(10))
        stages.forEachIndexed { index, title ->
            val x = left + index * (stageWidth + gap)
            val rect = RectF(x, y - dp(18), x + stageWidth, y + dp(18))
            canvas.drawRoundRect(rect, dp(5), dp(5), fill); canvas.drawRoundRect(rect, dp(5), dp(5), border)
            val oldSize = textPaint.textSize
            if (textPaint.measureText(title) > stageWidth - dp(4)) textPaint.textSize = sp(9)
            canvas.drawText(title, x + stageWidth / 2, y + textPaint.textSize / 3, textPaint)
            textPaint.textSize = oldSize
            if (index < stages.lastIndex) canvas.drawLine(x + stageWidth, y, x + stageWidth + gap, y, accent)
        }
    }

    private fun drawWave(canvas: Canvas) {
        val (left, right) = bounds(); val y = baseline(); val path = Path()
        for (i in 0..80) {
            val x = left + (right - left) * i / 80f
            val point = y - dp(28) * sin(2 * Math.PI * i / 80).toFloat()
            if (i == 0) path.moveTo(x, point) else path.lineTo(x, point)
        }
        canvas.drawPath(path, accent); canvas.drawLine(left, y + dp(38), right, y + dp(38), line)
        canvas.drawText("One wavelength", width / 2f, y + dp(54), textPaint)
    }

    private fun drawReflection(canvas: Canvas) {
        val (left, right) = bounds(); val center = (left + right) / 2; val y = baseline()
        canvas.drawLine(left, y - dp(14), center - dp(8), y - dp(14), line)
        canvas.drawLine(center - dp(8), y + dp(14), left, y + dp(14), accent)
        canvas.drawLine(center, y - dp(30), center, y + dp(30), border)
        canvas.drawText("INCIDENT →", (left + center) / 2, y - dp(23), textPaint)
        canvas.drawText("← REFLECTED", (left + center) / 2, y + dp(31), textPaint)
        canvas.drawText("LOAD", (center + right) / 2, y + dp(4), textPaint)
    }

    private fun drawNoise(canvas: Canvas) {
        val y = baseline(); val left = width * 0.32f; val right = width * 0.68f
        canvas.drawRect(left - dp(25), y - dp(30), left + dp(25), y + dp(20), fill)
        canvas.drawRect(right - dp(25), y - dp(10), right + dp(25), y + dp(20), fill)
        canvas.drawLine(left - dp(30), y + dp(20), right + dp(30), y + dp(20), line)
        canvas.drawText("SIGNAL", left, y + dp(37), textPaint); canvas.drawText("NOISE", right, y + dp(37), textPaint)
    }

    private fun drawWifiRaster(canvas: Canvas) {
        val (left, right) = bounds(); val y = baseline()
        val examples = when (id) {
            "wifi24" -> listOf(1 to 2412, 6 to 2437, 11 to 2462)
            "wifi5" -> listOf(36 to 5180, 100 to 5500, 149 to 5745)
            else -> listOf(1 to 5955, 97 to 6435, 193 to 6915)
        }
        val min = examples.first().second; val max = examples.last().second
        canvas.drawLine(left, y, right, y, line)
        examples.forEach { (channel, frequency) ->
            val x = left + (right - left) * (frequency - min).toFloat() / (max - min)
            canvas.drawLine(x, y - dp(8), x, y + dp(8), accent)
            canvas.drawText("$channel", x, y - dp(14), textPaint)
            canvas.drawText("$frequency", x, y + dp(24), textPaint)
        }
        textPaint.textSize = sp(10); textPaint.color = Color.parseColor("#a9c7d4")
        canvas.drawText("Tick = example channel center (MHz)", width / 2f, y + dp(45), textPaint)
    }
}
