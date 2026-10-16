package com.veilbreaker.companion

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.*
import android.telephony.*
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.time.Instant

/** Explicit foreground equipment connection and bounded captures. */
class MainActivity : Activity() {
    private val handler=Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var preview: TextView
    private lateinit var usbStatus: TextView
    private lateinit var subscriptions: Spinner
    private lateinit var cellularChoice: CheckBox
    private lateinit var locationChoice: CheckBox
    private lateinit var captureButton: Button
    private lateinit var exportButton: Button
    private lateinit var location: PhoneLocation
    private var choices: List<SubscriptionInfo> = emptyList()
    private var generation=0
    private var pending=false
    private var connection: UsbConnection?=null
    private var endpoint: LoopbackEndpoint?=null
    private var capture: JSONObject?=null
    private var exportText: String?=null
    private var raw=false
    private val permissions=arrayOf(Manifest.permission.READ_PHONE_STATE,Manifest.permission.ACCESS_COARSE_LOCATION,Manifest.permission.ACCESS_FINE_LOCATION)
    private fun dp(n:Int)=(n*resources.displayMetrics.density).toInt()
    private fun background(color:String)=GradientDrawable().apply { setColor(Color.parseColor(color)); cornerRadius=dp(12).toFloat() }

    override fun onCreate(state:Bundle?) {
        setTheme(android.R.style.Theme_Material_NoActionBar)
        super.onCreate(state)
        location=PhoneLocation(this)
        window.statusBarColor=Color.parseColor("#0d1520")
        window.navigationBarColor=Color.parseColor("#0d1520")
        val scroll=ScrollView(this).apply { setBackgroundColor(Color.parseColor("#0d1520")); isFillViewport=true }
        val root=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setPadding(dp(20),dp(32),dp(20),dp(28)) }
        scroll.addView(root);setContentView(scroll)
        fun text(parent:LinearLayout,value:String,size:Float=14f)=TextView(this).apply {
            text=value;textSize=size;setTextColor(Color.parseColor("#b8c9da"));setPadding(0,dp(6),0,dp(8));parent.addView(this)
        }
        fun card(title:String):LinearLayout {
            val box=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(16),dp(12),dp(16),dp(16));background=background("#152233") }
            root.addView(box,LinearLayout.LayoutParams(-1,-2).apply { topMargin=dp(14) })
            text(box,title,18f).apply { setTextColor(Color.parseColor("#63dec8"));setTypeface(null,Typeface.BOLD) }
            return box
        }
        fun button(parent:LinearLayout,title:String,primary:Boolean=false,action:()->Unit)=Button(this).apply {
            text=title;isAllCaps=false;minHeight=dp(48)
            backgroundTintList=android.content.res.ColorStateList.valueOf(Color.parseColor(if(primary) "#58d3be" else "#24364c"))
            setTextColor(Color.parseColor(if(primary) "#0c2026" else "#e5edf5"));setOnClickListener { action() };parent.addView(this)
        }
        text(root,"VEILBREAKER",27f).apply { setTypeface(null,Typeface.BOLD);setTextColor(Color.WHITE) }
        text(root,"FIELD COMPANION  /  0.4",12f).setTextColor(Color.parseColor("#63dec8"))
        text(root,"Your phone is a field sensor. Choose what to share, connect to Desktop, and keep this app visible during your survey.")
        val inputs=card("1  Choose inputs")
        cellularChoice=CheckBox(this).apply { text="Cellular measurements";isChecked=true;inputs.addView(this) }
        locationChoice=CheckBox(this).apply { text="Record phone location (GPS)";isChecked=false;inputs.addView(this) }
        text(inputs,"Location is optional. Coordinates are recorded only when enabled. No SIM is needed for location-only capture.")
        button(inputs,"Permissions and refresh SIMs") { if(allowed()) refresh() else requestPermissions(permissions,1) }
        subscriptions=Spinner(this);inputs.addView(subscriptions)
        val connect=card("2  Connect to Desktop")
        button(connect,"Connect to Veilbreaker",true) { armUsb() }
        usbStatus=text(connect,"Disconnected · USB cable and debugging approval required. No code needs to be typed.")
        button(connect,"Stop and disconnect") { stopUsb();cancelPending() }
        val local=card("3  Capture and review")
        captureButton=button(local,"Capture on phone") { takeSnapshot(null) }
        status=text(local,"Choose inputs and grant permissions to begin.")
        preview=text(local,"No saved capture.")
        button(local,"Show / hide technical details") { raw=!raw;showCapture() }
        exportButton=button(local,"Export capture") {
            capture?.let {
                exportText=it.toString(2)
                startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE);type="application/json";putExtra(Intent.EXTRA_TITLE,"veilbreaker-${it.getString("capture_id")}.json")
                },2)
            }
        }
        cellularChoice.setOnCheckedChangeListener { _,_->refresh() }
        locationChoice.setOnCheckedChangeListener { _,_->refresh() }
        capture=try { JSONObject(filesDir.resolve("last-capture.json").readText()) } catch(_:Exception) { null }
        showCapture();refresh()
    }
    private fun allowed() = (!cellularChoice.isChecked || (checkSelfPermission(Manifest.permission.READ_PHONE_STATE)==PackageManager.PERMISSION_GRANTED && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED)) &&
        (!locationChoice.isChecked || checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED)
    private fun refresh() {
        if(connection!=null) return
        choices=try { if(checkSelfPermission(Manifest.permission.READ_PHONE_STATE)==PackageManager.PERMISSION_GRANTED) getSystemService(SubscriptionManager::class.java).activeSubscriptionInfoList ?: emptyList() else emptyList() } catch(_:SecurityException) { emptyList() }
        val selected=subscriptions.selectedItemPosition
        subscriptions.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,listOf("Choose a SIM")+choices.map { "SIM ${it.simSlotIndex+1} · ${it.displayName}" })
        if(selected in 1..choices.size) subscriptions.setSelection(selected)
        subscriptions.isEnabled=cellularChoice.isChecked
        captureButton.isEnabled=allowed() && (cellularChoice.isChecked || locationChoice.isChecked) && !pending
    }
    override fun onRequestPermissionsResult(code:Int,p:Array<out String>,results:IntArray) { super.onRequestPermissionsResult(code,p,results);if(code==1) refresh() }
    private fun takeSnapshot(target:UsbSession?) {
        if(pending) return
        val useCell=connection?.cellular ?: cellularChoice.isChecked
        val useLocation=connection?.location ?: locationChoice.isChecked
        if(!allowed()) { target?.finish("partial");status.text="Permission unavailable. Stop and grant permissions again.";return }
        val selected=choices.getOrNull(subscriptions.selectedItemPosition-1)
        if(useCell && selected==null) { target?.finish("partial");status.text="Choose a SIM for cellular measurements.";return }
        if(!useCell && !useLocation) { status.text="Choose at least one input.";return }
        if(target==null) location.start(useLocation)
        val epoch=++generation;pending=true;lockInputs(true)
        val started=Instant.now().toString()
        status.text=if(useCell) "Collecting cellular measurements…" else "Collecting location…"
        fun finish(cells:List<CellInfo>?,error:String?) {
            if(epoch!=generation || !pending || (target!=null && target!==connection?.session)) return
            pending=false
            val elapsed=SystemClock.elapsedRealtime()
            try {
                val stillPresent=!useCell || getSystemService(SubscriptionManager::class.java).activeSubscriptionInfoList?.any { it.subscriptionId==selected!!.subscriptionId }==true
                val source=if(stillPresent) cells.orEmpty() else emptyList()
                val outcome=if(error!=null || !stillPresent || (useCell && source.isEmpty()) || source.size>256) "partial" else "complete"
                val snapshot=CaptureSerializer.envelope(Build.MANUFACTURER,Build.MODEL,Build.VERSION.RELEASE,Build.VERSION.SDK_INT,"0.4.0-dev",
                    source.take(256).map { CellularSnapshot.cell(it,elapsed) },elapsed,outcome,listOfNotNull(error),started)
                val observation=snapshot.getJSONArray("observations").getJSONObject(0)
                snapshot.getJSONObject("collection").put("inputs",JSONObject().put("cellular",useCell).put("location",useLocation))
                if(useLocation) observation.put("location",location.atReceipt(elapsed))
                if(useCell) {
                    val manager=getSystemService(TelephonyManager::class.java).createForSubscriptionId(selected!!.subscriptionId)
                    snapshot.getJSONArray("subscriptions").getJSONObject(0).put("network_operator",manager.networkOperatorName).put("sim_carrier",selected.carrierName?.toString() ?: "")
                } else {
                    snapshot.getJSONArray("subscriptions").getJSONObject(0).put("key","location-only").put("kind","location_only")
                    observation.put("subscription_key","location-only")
                }
                if(target!=null) { target.accept(snapshot);if(!stillPresent || !allowed()) target.finish("partial") }
                else save(snapshot)
                val loc=observation.optJSONObject("location")
                status.text=if(loc==null) "Capture saved · location off" else "Capture saved · " + locationStatus(loc)
            } catch(_:Exception) { target?.finish("partial");status.text="Capture unavailable. Previous evidence is retained." }
            if(target==null) location.stop()
            lockInputs(connection!=null);showCapture()
        }
        if(!useCell) {
            val deadline=SystemClock.elapsedRealtime()+30000
            val waitForFix=object:Runnable {
                override fun run() {
                    if(epoch!=generation || !pending) return
                    val state=location.atReceipt(SystemClock.elapsedRealtime()).optString("status")
                    if(target!=null || state!="unavailable" || SystemClock.elapsedRealtime()>=deadline) finish(emptyList(),null)
                    else { status.text="Waiting for GPS fix… Keep the phone near a clear view of the sky.";handler.postDelayed(this,1000) }
                }
            }
            handler.postDelayed(waitForFix,1000);return
        }
        handler.postDelayed({ finish(null,"Cell request timed out") },15000)
        try {
            getSystemService(TelephonyManager::class.java).createForSubscriptionId(selected!!.subscriptionId).requestCellInfoUpdate(mainExecutor,object:TelephonyManager.CellInfoCallback() {
                override fun onCellInfo(info:MutableList<CellInfo>) { finish(info,null) }
                override fun onError(code:Int,detail:Throwable?) { finish(null,"Cell information unavailable") }
            })
        } catch(_:Exception) { finish(null,"Cell information unavailable") }
    }
    private fun locationStatus(loc:JSONObject):String {
        if(loc.optString("status")!="available") return when(loc.optString("status")) { "permission_denied"->"Location permission unavailable";"disabled"->"Location off";else->"Waiting for fix / no fix" }
        val quality=when { loc.optBoolean("mock")->"Test location";loc.optLong("fix_age_ms",Long.MAX_VALUE)>10000->"Old fix";loc.optDouble("horizontal_accuracy_m",Double.MAX_VALUE)>25->"Low accuracy";else->"Location ready" }
        return "$quality · ±${loc.optDouble("horizontal_accuracy_m").toInt()} m · ${loc.optLong("fix_age_ms")/1000}s old"
    }
    private fun save(value:JSONObject) { capture=value;filesDir.resolve("last-capture.json").writeText(value.toString());showCapture() }
    private fun showCapture() {
        val value=capture
        preview.text=if(value==null) "No saved capture." else if(raw) value.toString(2).take(20000) else {
            val observations=value.getJSONArray("observations")
            val last=if(observations.length()>0) observations.getJSONObject(observations.length()-1) else null
            val lines=mutableListOf("${observations.length()} observations · ${value.getJSONObject("collection").optString("outcome")}")
            last?.optJSONObject("location")?.let { lines.add(locationStatus(it));if(it.optString("status")=="available") lines.add("${it.optDouble("latitude_deg")}, ${it.optDouble("longitude_deg")}") }
            last?.optJSONArray("cells")?.let { cells->for(i in 0 until cells.length()) {
                val cell=cells.getJSONObject(i)
                if(cell.optBoolean("registered")) {
                    lines.add("${cell.optString("radio")} · serving cell ${cell.getJSONObject("identity").optString("cell_id","unknown")}")
                    val signal=cell.getJSONObject("signal")
                    for(key in listOf("rsrp","rsrq","rssnr","ss_rsrp","ss_rsrq","ss_sinr")) signal.optJSONObject(key)?.let { q->if(!q.isNull("value")) lines.add("${key.uppercase().replace('_','-')}: ${q.opt("value")} ${q.optString("unit")}") }
            } } }
            lines.joinToString("\n")
        }
        exportButton.isEnabled=value!=null && !pending && connection==null
    }
    private fun lockInputs(locked:Boolean) { cellularChoice.isEnabled=!locked;locationChoice.isEnabled=!locked;subscriptions.isEnabled=!locked && cellularChoice.isChecked;captureButton.isEnabled=!locked && allowed() }
    private fun cancelPending() { generation++;pending=false;location.stop();lockInputs(connection!=null);showCapture() }
    private fun armUsb() {
        if(pending || connection!=null || !allowed() || (!cellularChoice.isChecked && !locationChoice.isChecked) || (cellularChoice.isChecked && subscriptions.selectedItemPosition<1)) { status.text="Choose inputs, grant permissions, and select a SIM if using cellular.";return }
        val conn=UsbConnection({SystemClock.elapsedRealtime()},cellularChoice.isChecked,locationChoice.isChecked,{session->takeSnapshot(session)},{save(it)},
            { generation++;pending=false;location.start(locationChoice.isChecked) },{ generation++;pending=false;location.stop() })
        connection=conn
        val pairing=UsbPairing({SystemClock.elapsedRealtime()},conn.token)
        try {
            endpoint=LoopbackEndpoint { name,token,body->
                val latch=java.util.concurrent.CountDownLatch(1);var response:JSONObject?=null
                handler.post {
                    try {
                        if(connection===conn) {
                            if(name=="pair" || name=="pair_status") {
                                val pairId=body.getString("pair_id")
                                val result=JSONObject().put("protocol",1).put("request_id",body.getString("request_id")).put("session_id",conn.id).put("status","armed").put("capabilities",conn.capabilities())
                                if(name=="pair") {
                                    pairing.begin(pairId,body.getString("code"))
                                    val survey=body.optBoolean("survey_mode",false)
                                    android.app.AlertDialog.Builder(this).setTitle("Connect to Veilbreaker?")
                                        .setMessage("Match Desktop code: ${body.getString("code")}\n" + if(survey) "Allow repeated survey tests while this app stays visible? Approval expires after 15 idle minutes or 60 total minutes." else "Allow one diagnostic capture?")
                                        .setPositiveButton("Codes match — connect") { _,_->runCatching { if(connection===conn) { pairing.approve(pairId);conn.approve(survey) } } }
                                        .setNegativeButton("Reject") { _,_->pairing.deny() }.setOnCancelListener { pairing.deny() }.show()
                                } else { val credential=pairing.poll(pairId);result.put("paired",credential!=null);if(credential!=null) result.put("token",credential) }
                                response=result
                            } else response=conn.command(name,token,body)
                        }
                    } catch(_:Exception) { } finally { latch.countDown() }
                }
                require(latch.await(2,java.util.concurrent.TimeUnit.SECONDS));response ?: throw IllegalArgumentException("Connection unavailable")
            }
            lockInputs(true);usbStatus.text="Ready for Desktop · confirm the matching code here. Keep this app visible."
            window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
            fun tick() { if(connection!==conn) return;conn.expire();handler.postDelayed({tick()},1000) };tick()
        } catch(_:Exception) { stopUsb();status.text="USB endpoint unavailable. Stop another companion and retry." }
    }
    private fun stopUsb() { endpoint?.close();endpoint=null;connection?.revoke();connection=null;location.stop();usbStatus.text="Disconnected · reconnect for another survey.";window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
    override fun onStop() { stopUsb();cancelPending();super.onStop() }
    @Deprecated("Platform result keeps companion dependency-light")
    override fun onActivityResult(request:Int,result:Int,data:Intent?) {
        super.onActivityResult(request,result,data)
        if(request==2 && result==RESULT_OK && data?.data!=null) try {
            contentResolver.openOutputStream(data.data!!,"wt")?.use { it.write((exportText ?: error("No export")).toByteArray(Charsets.UTF_8)) } ?: error("Cannot export")
            status.text="Capture exported."
        } catch(_:Exception) { status.text="Export failed. Saved capture remains available." }
        exportText=null
    }
}
