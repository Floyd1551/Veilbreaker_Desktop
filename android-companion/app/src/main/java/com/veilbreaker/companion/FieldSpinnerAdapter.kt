package com.veilbreaker.companion

import android.content.Context
import android.graphics.Color
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.TextView

/** Readable selected and popup rows in the dark instrument theme, including large text. */
internal class FieldSpinnerAdapter(context: Context, values: List<String>) :
    ArrayAdapter<String>(context, android.R.layout.simple_spinner_item, values) {
    private fun row(position: Int): TextView = TextView(context).apply {
        val density = resources.displayMetrics.density
        fun dp(n: Int) = (n * density).toInt()
        text = getItem(position).orEmpty()
        textSize = 14f
        setTextColor(Color.parseColor("#e8f5fa"))
        setBackgroundColor(Color.parseColor("#172a3b"))
        setPadding(dp(12), dp(10), dp(12), dp(10))
        minHeight = dp(48)
        gravity = Gravity.CENTER_VERTICAL
    }
    override fun getView(position: Int, convertView: View?, parent: ViewGroup): View = row(position)
    override fun getDropDownView(position: Int, convertView: View?, parent: ViewGroup): View = row(position)
}
