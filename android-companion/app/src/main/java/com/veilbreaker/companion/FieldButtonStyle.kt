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
        cornerRadius = 9 * density
    }
    backgroundTintList = ColorStateList(states, intArrayOf(
        Color.parseColor("#1b2935"), Color.parseColor(if (primary) "#43d7e3" else "#233e51")))
    setTextColor(ColorStateList(states, intArrayOf(
        Color.parseColor("#8ca0ae"), Color.parseColor(if (primary) "#06232a" else "#ffffff"))))
    isAllCaps = false
    minHeight = (48 * density).toInt()
    textSize = 13f
    elevation = 0f
}
