package com.veilbreaker.companion

import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.widget.Button

/** Consistent field controls, including readable disabled states. */
internal fun Button.styleFieldButton(primary: Boolean = false) {
    val density = resources.displayMetrics.density
    val states = arrayOf(intArrayOf(-android.R.attr.state_enabled), intArrayOf())
    background = GradientDrawable().apply {
        setColor(Color.WHITE)
        cornerRadius = 14 * density
    }
    backgroundTintList = ColorStateList(states, intArrayOf(
        Color.parseColor("#1b2933"), Color.parseColor(if (primary) "#78d8db" else "#29414d")))
    setTextColor(ColorStateList(states, intArrayOf(
        Color.parseColor("#91a5af"), Color.parseColor(if (primary) "#09272c" else "#edf5f8"))))
    isAllCaps = false
    minHeight = (48 * density).toInt()
    textSize = 13f
    elevation = 0f
}
