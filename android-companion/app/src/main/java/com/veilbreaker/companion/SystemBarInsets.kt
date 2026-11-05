package com.veilbreaker.companion

import android.os.Build
import android.view.View
import android.view.WindowInsets

/** Explicit safe-area padding for edge-to-edge enforcement on Android 15+. */
object SystemBarInsetsPolicy {
    data class Edges(val left: Int, val top: Int, val right: Int, val bottom: Int)

    fun padding(base: Edges, bars: Edges, api: Int): Edges =
        if (api < 35) base else Edges(base.left + bars.left, base.top + bars.top,
            base.right + bars.right, base.bottom + bars.bottom)
}

object SystemBarInsets {
    fun apply(root: View) {
        // Earlier Android versions already fit the default decor to system bars.
        if (Build.VERSION.SDK_INT < 35) return
        val base = SystemBarInsetsPolicy.Edges(root.paddingLeft, root.paddingTop, root.paddingRight, root.paddingBottom)
        root.setOnApplyWindowInsetsListener { view, insets ->
            val bars = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            val padding = SystemBarInsetsPolicy.padding(base,
                SystemBarInsetsPolicy.Edges(bars.left, bars.top, bars.right, bars.bottom), Build.VERSION.SDK_INT)
            view.setPadding(padding.left, padding.top, padding.right, padding.bottom)
            insets
        }
        root.requestApplyInsets()
    }
}
