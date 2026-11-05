package com.veilbreaker.companion

import android.Manifest
import android.annotation.SuppressLint
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.telephony.TelephonyManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/** User-requested foreground service-state snapshot; no privileged modem access. */
class CellConnectionWorkspace(context: Context, private val selectedSubscriptionId: () -> Int?) : LinearLayout(context) {
    private val output = TextView(context)
    private val refreshButton: Button
    private var requestGeneration = 0
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    init {
        orientation = VERTICAL
        addView(TextView(context).apply {
            text = "CONNECTION DETAILS"; textSize = 16f; setTypeface(null, Typeface.BOLD)
            setTextColor(Color.parseColor("#63d6ee")); setPadding(0, dp(10), 0, dp(6))
        })
        addView(TextView(context).apply {
            text = "Read the selected SIM's current public Android connection state. This is separate from a saved capture."
            textSize = 13f; setTextColor(Color.parseColor("#b8cbd9"))
        })
        refreshButton = Button(context).apply {
            text = "Refresh cellular connection"; isAllCaps = false; minHeight = dp(48); setOnClickListener { refresh() }
        }
        addView(refreshButton)
        output.textSize = 13f; output.setTextColor(Color.parseColor("#e8f5fa")); output.setPadding(0, dp(8), 0, dp(8))
        output.text = "Choose a SIM, grant phone permission, then refresh."; addView(output)
    }
    fun selectionChanged() {
        requestGeneration++
        refreshButton.isEnabled = true
        output.text = "SIM selection changed. Refresh connection details for the selected SIM."
    }
    @SuppressLint("MissingPermission")
    private fun refresh() {
        val id = selectedSubscriptionId()
        if (id == null) { output.text = "Choose a SIM in Phone inputs before refreshing."; return }
        if (context.checkSelfPermission(Manifest.permission.READ_PHONE_STATE) != PackageManager.PERMISSION_GRANTED) {
            output.text = "Phone permission is required. Use Permissions and refresh SIMs above."; return
        }
        val generation = ++requestGeneration
        refreshButton.isEnabled = false; output.text = "Reading Android connection state…"
        Thread {
            fun <T> safe(block: () -> T): T? = try { block() } catch (_: RuntimeException) { null }
            val manager = safe { context.getSystemService(TelephonyManager::class.java).createForSubscriptionId(id) }
            fun display(value: String?) = value?.takeIf { it.isNotBlank() } ?: "Not exposed"
            val operator = safe { manager?.networkOperatorName }
            val number = safe { manager?.networkOperator }
            val data = safe { manager?.dataNetworkType }?.let(CellConnectionLabels::radio) ?: "Not exposed"
            val voice = safe { manager?.voiceNetworkType }?.let(CellConnectionLabels::radio) ?: "Not exposed"
            val state = safe { manager?.dataState }?.let(CellConnectionLabels::dataState) ?: "Not exposed"
            val roaming = if (number.isNullOrBlank()) "Not exposed" else safe { manager?.isNetworkRoaming }?.let { if (it) "Yes" else "No" } ?: "Not exposed"
            val details = "Operator: ${display(operator)}\nNetwork MCC/MNC: ${display(number)}\nVoice technology: $voice\nData technology: $data\nData connection state: $state\nRoaming: $roaming\n\n" +
                "Android may report LTE as the data technology during 5G NSA; a 5G override, raw modem messages and all aggregated bands are not guaranteed by these fields. Connection state is not a throughput or internet test."
            post {
                if (isAttachedToWindow && generation == requestGeneration) {
                    refreshButton.isEnabled = true
                    output.text = if (selectedSubscriptionId() == id) details else "SIM selection changed. Refresh connection details for the selected SIM."
                }
            }
        }.apply { name = "Veilbreaker cellular connection"; start() }
    }
}
