package com.veilbreaker.companion

import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.graphics.pdf.PdfDocument
import org.json.JSONObject
import java.io.OutputStream

/** Render an offline, bounded readable PDF; original capture remains separate. */
object CaptureReportPdf {
    fun write(capture: JSONObject, plan: JSONObject, output: OutputStream) {
        val content = CaptureReportContent.build(capture, plan)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG).apply { color=Color.rgb(25,36,48); textSize=10f; typeface=Typeface.create(Typeface.SANS_SERIF,Typeface.NORMAL) }
        val lines=ArrayList<String>()
        for (paragraph in content.split('\n')) {
            var rest=paragraph
            if(rest.isEmpty()) { lines.add(""); continue }
            while(rest.isNotEmpty() && lines.size < 1000) {
                var count=paint.breakText(rest,true,500f,null).coerceAtLeast(1)
                if(count<rest.length) {
                    val space=rest.lastIndexOf(' ',count-1)
                    if(space>count/2) count=space
                }
                lines.add(rest.substring(0,count).trimEnd()); rest=rest.substring(count).trimStart()
            }
            if(lines.size >= 1000) break
        }
        if(lines.size >= 1000) lines[999]="Report truncated; export the original JSON for complete evidence."
        val pdf=PdfDocument()
        try {
            for ((index, pageLines) in lines.chunked(50).withIndex()) {
                val page=pdf.startPage(PdfDocument.PageInfo.Builder(612,792,index+1).create())
                val canvas=page.canvas; canvas.drawColor(Color.WHITE)
                var y=42f
                for(line in pageLines) { canvas.drawText(line,46f,y,paint); y+=14f }
                pdf.finishPage(page)
            }
            pdf.writeTo(output)
        } finally { pdf.close() }
    }
}
