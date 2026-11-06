package com.veilbreaker.companion

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.View
import android.widget.LinearLayout
import android.widget.TextView
import java.util.Locale

/** Static, offline reference tables; values are reference calculations, never measurements. */
internal object ReferenceVisualData {
    data class Table(val title: String, val left: String, val right: String, val rows: List<Pair<String, String>>, val note: String)
    private fun t(title: String, left: String, right: String, rows: List<Pair<String, String>>, note: String) = Table(title, left, right, rows, note)
    private val dbm = t("Power conversion", "dBm", "Power (mW)", listOf("−20" to "0.01", "−10" to "0.1", "0" to "1", "10" to "10", "20" to "100", "30" to "1,000 (1 W)"),
        "Calculated: mW = 10^(dBm/10). No antenna gain or cable loss is included.")
    private val ratios = t("Power ratios", "Power ratio", "Change (dB)", listOf("0.1×" to "−10", "0.5×" to "−3.01", "1×" to "0", "2×" to "+3.01", "10×" to "+10", "100×" to "+20"),
        "Approximate values. Power ratios use 10 log₁₀; voltage ratios use 20 log₁₀ with compatible impedances.")
    private val cidr = t("IPv4 prefix reference", "Prefix", "Mask · total addresses", listOf(
        "/24" to "255.255.255.0 · 256", "/25" to "255.255.255.128 · 128", "/26" to "255.255.255.192 · 64", "/27" to "255.255.255.224 · 32", "/28" to "255.255.255.240 · 16", "/29" to "255.255.255.248 · 8", "/30" to "255.255.255.252 · 4", "/31" to "255.255.255.254 · 2", "/32" to "255.255.255.255 · 1"),
        "Totals include all addresses; usable host counts depend on context and policy. RFC 4632; /31 point-to-point behavior: RFC 3021.")
    private val psc = t("6 GHz preferred scanning channels", "Channel", "Center frequency (MHz)",
        (0..14).map { 5 + 16 * it }.map { ch -> ch.toString() to (WirelessCalculators.channelToMhz(WirelessCalculators.Band.GHZ_6, ch) ?: error("Invalid 6 GHz PSC grid")).toString() },
        "PSC list: Cisco Wi-Fi 6E operations; frequency numbering: Android ScanResult / IEEE 802.11 channel grid. Channel listing does not imply regional authorization, AP mode or power limits.")
    private val channels = t("Common 2.4 GHz centers", "Channel", "Center (MHz)", listOf("1" to "2,412", "6" to "2,437", "11" to "2,462"),
        "Nominal 20 MHz channel scheme only. Spectrum masks extend beyond nominal width; availability and allowed use vary by region.")
    private val noise = t("Ideal thermal noise at 290 K", "Bandwidth", "Noise power (dBm)", listOf(
        "1 Hz" to "−174", "1 kHz" to "−144", "1 MHz" to "−114", "20 MHz" to "−101.0", "100 MHz" to "−94"),
        "Calculated: −174 + 10 log₁₀(bandwidth in Hz). Approximate matched thermal noise; excludes receiver noise figure and interference. Keysight noise-figure guidance.")
    private val wavelength = t("Free-space wavelength", "Frequency", "Wavelength (m)", listOf("700 MHz" to "0.428", "2.4 GHz" to "0.125", "5 GHz" to "0.060", "28 GHz" to "0.0107"),
        "Calculated using c/f in free space; wavelength in cables and materials depends on velocity factor.")
    private val mismatch = t("Ideal mismatch comparison", "VSWR", "Return loss · reflected power", listOf("1.0:1" to "∞ dB · 0%", "1.2:1" to "20.83 dB · 0.83%", "1.5:1" to "13.98 dB · 4%", "2.0:1" to "9.54 dB · 11.11%", "3.0:1" to "6.02 dB · 25%"),
        "Single-interface ideal calculations from |Γ| = (VSWR−1)/(VSWR+1); not a measured match or cable-loss estimate.")
    private val cell = t("Phone cellular metric units", "Reference signal", "Reported units", listOf("LTE RSRP" to "dBm", "LTE RSRQ" to "dB", "LTE RSSNR" to "dB", "NR SS-RSRP" to "dBm", "NR SS-RSRQ" to "dB", "NR SS-SINR" to "dB"),
        "LTE and NR are distinct reference signals. Values can be unavailable or cached; no universal quality threshold is implied. Source: Android CellSignalStrength LTE/NR APIs.")
    private val privateRanges = t("Private IPv4 blocks", "Prefix", "Inclusive range", listOf("10.0.0.0/8" to "10.0.0.0–10.255.255.255", "172.16.0.0/12" to "172.16.0.0–172.31.255.255", "192.168.0.0/16" to "192.168.0.0–192.168.255.255"),
        "RFC 1918. Private addressing is not a security control and does not describe every special-use address range.")

    fun table(id: String): Table? = when (id) {
        "rf-power", "expanded-dbm-table" -> dbm
        "expanded-db-ratio-table" -> ratios
        "expanded-cidr", "expanded-cidr-table" -> cidr
        "expanded-wifi-6" -> psc
        "wifi-channels", "expanded-wifi-24" -> channels
        "rf-noise", "expanded-noise-figure" -> noise
        "expanded-wavelength" -> wavelength
        "expanded-reflection" -> mismatch
        "cell-power", "cell-quality", "expanded-cell-rsrp", "expanded-cell-nr" -> cell
        "expanded-ipv4-private" -> privateRanges
        else -> null
    }

    fun hasChannelDiagram(id: String) = id == "wifi-channels" || id == "expanded-wifi-24"
}

/** Parent owns scrolling. Every row wraps on narrow screens; no horizontal scrolling is needed. */
internal object ReferenceVisuals {
    fun addTo(parent: LinearLayout, entryId: String): Boolean {
        val table = ReferenceVisualData.table(entryId)
        val diagram = ReferenceVisualData.hasChannelDiagram(entryId)
        if (diagram) parent.addView(ReferenceChannelDiagram(parent.context), LinearLayout.LayoutParams(-1, -2))
        if (table != null) parent.addView(tableView(parent.context, table), LinearLayout.LayoutParams(-1, -2))
        return diagram || table != null
    }

    private fun tableView(context: Context, table: ReferenceVisualData.Table): LinearLayout {
        fun dp(n: Int) = (n * context.resources.displayMetrics.density).toInt()
        fun label(value: String, bold: Boolean, color: String) = TextView(context).apply {
            text = value; textSize = 12f; setTextColor(Color.parseColor(color)); if (bold) setTypeface(null, Typeface.BOLD)
            setPadding(dp(7), dp(6), dp(7), dp(6)); setLineSpacing(dp(1).toFloat(), 1f)
        }
        val panel = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL; setPadding(dp(6), dp(6), dp(6), dp(6))
            background = GradientDrawable().apply { setColor(Color.parseColor("#0b1b29")); cornerRadius = dp(8).toFloat(); setStroke(dp(1), Color.parseColor("#29495a")) }
        }
        panel.addView(label(table.title.uppercase(Locale.ROOT), true, "#79dce7"))
        fun row(left: String, right: String, header: Boolean, alternate: Boolean) = LinearLayout(context).apply {
            orientation = LinearLayout.HORIZONTAL
            setBackgroundColor(Color.parseColor(if (header) "#18394a" else if (alternate) "#102838" else "#0b1b29"))
            addView(label(left, header, if (header) "#e8f5fa" else "#c3d8e2"), LinearLayout.LayoutParams(0, -2, 0.40f))
            addView(label(right, header, if (header) "#e8f5fa" else "#e5f3f8"), LinearLayout.LayoutParams(0, -2, 0.60f))
        }
        panel.addView(row(table.left, table.right, true, false))
        table.rows.forEachIndexed { index, item -> panel.addView(row(item.first, item.second, false, index % 2 == 1)) }
        panel.addView(label(table.note, false, "#a9c3cf"))
        return panel
    }
}

/** Widths and centers are idealized; not a spectrum trace or measured occupancy. */
private class ReferenceChannelDiagram(context: Context) : View(context) {
    private val density = resources.displayMetrics.density
    private val scaled = resources.displayMetrics.scaledDensity
    private val line = Paint(Paint.ANTI_ALIAS_FLAG).apply { strokeWidth = 2 * density; color = Color.parseColor("#3e6478"); style = Paint.Style.STROKE }
    private val bar = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; strokeWidth = 3 * density }
    private val text = Paint(Paint.ANTI_ALIAS_FLAG).apply { color = Color.parseColor("#d3e8ef"); textSize = 11 * scaled; textAlign = Paint.Align.CENTER; typeface = Typeface.DEFAULT_BOLD }
    init { importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_YES; contentDescription = "Conceptual 2.4 gigahertz 20 megahertz channel diagram: channels 1, 6 and 11 centered at 2412, 2437 and 2462 megahertz. Not a measured spectrum or authorization." }
    override fun onMeasure(widthMeasureSpec: Int, heightMeasureSpec: Int) {
        val height = (130 * density + 20 * scaled).toInt()
        setMeasuredDimension(resolveSize((280 * density).toInt(), widthMeasureSpec), resolveSize(height, heightMeasureSpec))
    }
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.parseColor("#0b1b29"))
        val pad = 20 * density; val y = height * 0.61f; val span = (width - 2 * pad).coerceAtLeast(1f)
        canvas.drawLine(pad, y, width - pad, y, line)
        val centers = intArrayOf(2412, 2437, 2462); val colors = intArrayOf(0xff59d4e6.toInt(), 0xff8bdabf.toInt(), 0xff88aee9.toInt())
        for (i in centers.indices) {
            val center = pad + span * (centers[i] - 2400) / 75f
            val half = span * 10 / 75f
            bar.color = colors[i]
            canvas.drawRect(center - half, y - 30 * density, center + half, y, bar)
            canvas.drawText("Ch ${listOf(1, 6, 11)[i]}", center, y - 36 * density, text)
            canvas.drawText(centers[i].toString(), center, y + 17 * density, text)
        }
        val originalSize = text.textSize
        val title = "20 MHz · NOT MEASURED"
        val maxWidth = (width - 2 * pad).coerceAtLeast(1f)
        if (text.measureText(title) > maxWidth) text.textSize *= maxWidth / text.measureText(title)
        canvas.drawText(title, width / 2f, 18 * scaled, text)
        text.textSize = originalSize
        canvas.drawText("Center frequency (MHz)", width / 2f, height - 10 * density, text)
    }
}
