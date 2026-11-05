package com.veilbreaker.companion

import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.hardware.usb.UsbManager
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/** Read-only descriptor inventory: never requests permission or opens a peripheral. */
class UsbHardwareWorkspace(context: Context) : LinearLayout(context) {
    private val result = TextView(context)
    private fun dp(n: Int) = (n * resources.displayMetrics.density).toInt()
    init {
        orientation = VERTICAL
        addView(TextView(context).apply {
            text = "USB PERIPHERALS"; textSize = 16f; setTypeface(null, Typeface.BOLD)
            setTextColor(Color.parseColor("#63d6ee")); setPadding(0, dp(10), 0, dp(6))
        })
        addView(TextView(context).apply {
            text = "Check devices attached through a USB-C adapter or hub. This only reads Android's device list; no device is opened, controlled, or used for RF capture."
            textSize = 13f; setTextColor(Color.parseColor("#b8cbd9")); setPadding(0, dp(3), 0, dp(6))
        })
        addView(Button(context).apply {
            text = "Refresh USB devices"; isAllCaps = false; minHeight = dp(48)
            setOnClickListener { refresh() }
        })
        result.textSize = 13f; result.setTextColor(Color.parseColor("#e8f5fa"))
        result.setPadding(0, dp(8), 0, dp(8)); addView(result)
        result.text = "Tap Refresh to inspect Android's current USB device list."
    }
    private fun refresh() {
        if (!context.packageManager.hasSystemFeature(PackageManager.FEATURE_USB_HOST)) {
            result.text = "Android does not report USB host support on this device."
            return
        }
        val manager = context.getSystemService(Context.USB_SERVICE) as? UsbManager
        if (manager == null) { result.text = "USB service is unavailable."; return }
        result.text = try {
            val devices = manager.deviceList.values.sortedWith(compareBy({ it.vendorId }, { it.productId }))
            if (devices.isEmpty()) "No USB peripherals are visible in host mode. Check the hub, cable, power and Android USB mode."
            else {
                val lines = devices.take(32).map { device ->
                    val classes = (0 until minOf(device.interfaceCount, 32)).map { device.getInterface(it).interfaceClass }.distinct().sorted()
                    "${UsbInventoryModel.kind(device.vendorId, device.productId)} · ${UsbInventoryModel.ids(device.vendorId, device.productId)}\n" +
                        "USB device class ${device.deviceClass}; interface classes ${if (classes.isEmpty()) "not reported" else classes.joinToString()}."
                }.toMutableList()
                if (devices.size > 32) lines.add("Additional devices omitted from display.")
                lines.add("Identification is based on USB descriptors only. SDR capture and direct USB device control are not yet available.")
                lines.joinToString("\n\n")
            }
        } catch (_: RuntimeException) { "Android could not read the USB device list. Try refreshing after reconnecting the hub." }
    }
}
