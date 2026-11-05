package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.text.Editable
import android.text.InputFilter
import android.text.TextWatcher
import android.view.View
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import org.json.JSONObject

/** Scrolling is supplied by the host. Never changes or starts a capture. */
class CellInventoryWorkspace(context:Context): LinearLayout(context) {
    private val cards=LinearLayout(context)
    private val search=EditText(context)
    private var group:CellInventoryModel.Group?=null
    private var data=CellInventoryModel.Inventory(emptyList(),0,0)
    private var unavailable=false
    private var expanded:CellInventoryModel.Cell?=null
    private fun dp(n:Int)=(n*resources.displayMetrics.density).toInt()
    private fun text(value:String,size:Float=13f,bright:Boolean=false)=TextView(context).apply {
        text=value;textSize=size;setTextColor(Color.parseColor(if(bright) "#e8f5fa" else "#b8cbd9"))
        if(bright) setTypeface(null,Typeface.BOLD)
        setPadding(0,dp(3),0,dp(4))
    }
    init {
        orientation=VERTICAL
        addView(text("CELL INVENTORY",16f,true).apply { setTextColor(Color.parseColor("#63d6ee")) })
        addView(text("Latest saved observation per SIM · recorded cell reports, not an exhaustive scan. Search radio, band, PCI or identity.",12f))
        search.apply {
            hint="Search cells…";contentDescription="Search captured cellular inventory";setSingleLine(true)
            setTextColor(Color.WHITE);setHintTextColor(Color.LTGRAY);filters=arrayOf(InputFilter.LengthFilter(120))
            addTextChangedListener(object:TextWatcher {
                override fun beforeTextChanged(s:CharSequence?,start:Int,count:Int,after:Int) {}
                override fun onTextChanged(s:CharSequence?,start:Int,before:Int,count:Int) { expanded=null;render() }
                override fun afterTextChanged(s:Editable?) {}
            })
        }
        addView(search,LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT))
        addView(Spinner(context).apply {
            contentDescription="Cell role filter"
            adapter=ArrayAdapter(context,android.R.layout.simple_spinner_dropdown_item,listOf("All cell roles","Serving","Neighbors","Unclassified"))
            onItemSelectedListener=object:AdapterView.OnItemSelectedListener {
                override fun onNothingSelected(parent:AdapterView<*>?) {}
                override fun onItemSelected(parent:AdapterView<*>?,view:View?,position:Int,id:Long) {
                    group=when(position) { 1->CellInventoryModel.Group.SERVING;2->CellInventoryModel.Group.NEIGHBOR;3->CellInventoryModel.Group.UNCLASSIFIED;else->null }
                    expanded=null;render()
                }
            }
        },LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT))
        cards.orientation=VERTICAL;addView(cards)
        render()
    }
    fun showCapture(capture:JSONObject?, plan:JSONObject?) {
        val result=runCatching { CellInventoryModel.build(capture,plan) }
        unavailable=result.isFailure
        data=result.getOrElse { CellInventoryModel.Inventory(emptyList(),0,0) }
        expanded=null;render()
    }
    private fun render() {
        cards.removeAllViews()
        if(unavailable) { cards.addView(text("Cell inventory unavailable. The saved capture was not changed; raw JSON remains available."));return }
        if(data.total==0) { cards.addView(text("No cells in the latest saved observations. Capture again if appropriate; Android may expose none.")); return }
        val selected=CellInventoryModel.filter(data.cells,group,search.text?.toString().orEmpty())
        cards.addView(text("${selected.size} matching shown candidates · ${data.total} cells in latest observations" +
            if(data.omitted>0) " · ${data.omitted} omitted from this inventory" else "",12f))
        if(selected.isEmpty()) { cards.addView(text("No matching cells in the displayed inventory."));return }
        selected.take(30).forEach { cell ->
            val card=LinearLayout(context).apply {
                orientation=VERTICAL;setPadding(dp(12),dp(9),dp(12),dp(10))
                background=GradientDrawable().apply { setColor(Color.parseColor("#112335"));cornerRadius=dp(10).toFloat();setStroke(dp(1),Color.parseColor("#294052")) }
            }
            cards.addView(card,LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT).apply { topMargin=dp(8) })
            card.addView(text("${cell.radio} · ${cell.role}",15f,true))
            card.addView(text("${cell.carrier} · ${cell.band}\n${cell.subscription} · ${cell.age}",12f))
            val identifier=cell.identity.filter { it.startsWith("PCI:") || it.startsWith("EARFCN:") || it.startsWith("NR-ARFCN:") || it.startsWith("ARFCN:") || it.startsWith("UARFCN:") }.take(2)
            if(identifier.isNotEmpty()) card.addView(text(identifier.joinToString(" · "),12f))
            card.addView(text(cell.metrics.take(3).joinToString(" · "),12f))
            val toggle=Button(context).apply {
                this.text=if(expanded===cell) "Hide details" else "Show details"
                contentDescription="${this.text}: ${cell.radio}, ${cell.role}, ${cell.subscription}"
                isAllCaps=false;minHeight=dp(48);setTextColor(Color.WHITE)
                backgroundTintList=ColorStateList.valueOf(Color.parseColor("#213e56"))
                setOnClickListener { expanded=if(expanded===cell) null else cell;render() }
            }
            card.addView(toggle,LayoutParams(LayoutParams.MATCH_PARENT,LayoutParams.WRAP_CONTENT))
            if(expanded===cell) {
                card.addView(text("Observation assembled: ${cell.received}",12f))
                cell.cellResponseReceived?.let { card.addView(text("Cell response received: $it · location may have been acquired separately",12f)) }
                card.addView(text("IDENTITY",11f,true).apply { setTextColor(Color.parseColor("#63d6ee")) })
                cell.identity.forEach { card.addView(text(it)) }
                card.addView(text("MEASUREMENTS",11f,true).apply { setTextColor(Color.parseColor("#63d6ee")) })
                cell.metrics.forEach { card.addView(text(it)) }
            }
        }
        if(selected.size>30) cards.addView(text("Showing 30 matching cells; refine the search to find others.",12f))
        cards.addView(text("Cell IDs and PCI do not establish a physical tower location. Sample age is at capture receipt, not current age.",12f))
    }
}
