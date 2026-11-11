package com.veilbreaker.companion

import android.Manifest
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.content.res.ColorStateList
import android.text.Editable
import android.text.TextWatcher
import android.os.*
import android.telephony.*
import android.util.AtomicFile
import android.view.Gravity
import android.view.View
import android.widget.*
import org.json.JSONObject
import java.time.Instant

/** Explicit foreground equipment connection and bounded captures. */
class MainActivity : Activity() {
    private val handler=Handler(Looper.getMainLooper())
    private lateinit var status: TextView
    private lateinit var inputReadiness: TextView
    private lateinit var preview: TextView
    private lateinit var cellularVisuals: CellularVisuals
    private lateinit var cellInventory: CellInventoryWorkspace
    private lateinit var liveDashboard: LiveDashboard
    private lateinit var surveyWorkspace: SurveyWorkspace
    private lateinit var networkTestWorkspace: NetworkTestWorkspace
    private lateinit var detailsButton: Button
    private lateinit var rawButton: Button
    private lateinit var usbStatus: TextView
    private lateinit var subscriptions: Spinner
    private lateinit var cellConnectionWorkspace: CellConnectionWorkspace
    private lateinit var liveCellWorkspace: LiveCellWorkspace
    private lateinit var cellularChoice: CheckBox
    private lateinit var locationChoice: CheckBox
    private lateinit var captureButton: Button
    private lateinit var cellularCaptureButton: Button
    private lateinit var cellularReviewButton: Button
    private lateinit var cellularCaptureReadiness: TextView
    private lateinit var cellularCaptureStatus: TextView
    private lateinit var exportButton: Button
    private lateinit var pdfButton: Button
    private lateinit var reportStatus: TextView
    private lateinit var reportSummary: TextView
    private lateinit var wifiButton: Button
    private lateinit var gpsButton: Button
    private lateinit var location: PhoneLocation
    private var choices: List<SubscriptionInfo> = emptyList()
    private var generation=0
    private var pending=false
    private var pendingSnapshotCompletion: ((Result<JSONObject>) -> Unit)? = null
    private var connection: UsbConnection?=null
    private var endpoint: LoopbackEndpoint?=null
    private var capture: JSONObject?=null
    private var exportText: String?=null
    private var exportPdfText: String?=null
    private var pdfExporting=false
    private val pages = mutableListOf<View>()
    private val navItems = mutableListOf<LinearLayout>()
    private val navLabels = mutableListOf<TextView>()
    private val navIcons = mutableListOf<ImageView>()
    private val diagnoseSections = mutableListOf<View>()
    private val diagnoseTabs = mutableListOf<TextView>()
    private lateinit var diagnoseScroll: ScrollView
    private var diagnoseSection = 0
    private var currentPage = WorkspacePage.LIVE
    private var previewMode="summary"
    private val channelPlan by lazy { JSONObject(assets.open("channel-bands.json").bufferedReader().use { it.readText() }) }
    private val permissions=arrayOf(Manifest.permission.READ_PHONE_STATE,Manifest.permission.ACCESS_COARSE_LOCATION,Manifest.permission.ACCESS_FINE_LOCATION)
    private fun dp(n:Int)=(n*resources.displayMetrics.density).toInt()
    private fun background(color:String)=GradientDrawable().apply { setColor(Color.parseColor(color)); cornerRadius=dp(12).toFloat() }
    private fun buttonColors(enabled:String, disabled:String)=ColorStateList(
        arrayOf(intArrayOf(-android.R.attr.state_enabled),intArrayOf()),
        intArrayOf(Color.parseColor(disabled),Color.parseColor(enabled)))

    private fun showPage(page: WorkspacePage) {
        if(currentPage==WorkspacePage.DIAGNOSE && page!=WorkspacePage.DIAGNOSE && ::networkTestWorkspace.isInitialized) networkTestWorkspace.cancel()
        if(currentPage==WorkspacePage.DIAGNOSE && page!=WorkspacePage.DIAGNOSE && ::liveCellWorkspace.isInitialized) liveCellWorkspace.stop()
        currentPage=page
        pages.forEachIndexed { index, view -> view.visibility=if(index==page.ordinal) View.VISIBLE else View.GONE }
        navItems.forEachIndexed { index, item ->
            val selected=index==page.ordinal
            item.background=background(if(selected) "#153c4a" else "#0a1b29")
            navLabels[index].setTextColor(Color.parseColor(if(selected) "#62e2ed" else "#a6bdcc"))
            navIcons[index].setColorFilter(Color.parseColor(if(selected) "#62e2ed" else "#a6bdcc"))
            item.isSelected=selected
        }
        if(page==WorkspacePage.SURVEY) surveyWorkspace.refresh()
    }

    private fun showDiagnoseSection(index: Int) {
        if (index !in diagnoseSections.indices) return
        if (diagnoseSection==2 && index!=2 && ::networkTestWorkspace.isInitialized) networkTestWorkspace.cancel()
        if (diagnoseSection==0 && index!=0 && ::liveCellWorkspace.isInitialized) liveCellWorkspace.stop()
        diagnoseSection=index
        diagnoseSections.forEachIndexed { i, view -> view.visibility=if(i==index) View.VISIBLE else View.GONE }
        diagnoseTabs.forEachIndexed { i, tab ->
            val selected=i==index
            tab.background=background(if(selected) "#2179ce" else "#1b3042")
            tab.setTextColor(Color.parseColor(if(selected) "#ffffff" else "#b3c7d5"))
            tab.isSelected=selected
        }
        if (::diagnoseScroll.isInitialized) diagnoseScroll.scrollTo(0,0)
    }

    private fun externalActionsEnabled() = WorkspaceNavigation.canOpenExternal(connection!=null,pending)
    private fun openWifi() { if(externalActionsEnabled()) startActivity(Intent(this,WifiSnapshotActivity::class.java)) }
    private fun openGps() { if(externalActionsEnabled()) startActivity(Intent(this,GpsMapActivity::class.java)) }
    private fun syncExternalActions() {
        val enabled=externalActionsEnabled()
        wifiButton.isEnabled=enabled;gpsButton.isEnabled=enabled
        if(::liveCellWorkspace.isInitialized) liveCellWorkspace.setCollectionBlocked(!enabled || !cellularChoice.isChecked)
        liveDashboard.setNavigationEnabled(enabled);surveyWorkspace.setExternalActionsEnabled(enabled)
        exportButton.isEnabled=enabled && capture!=null && !pdfExporting;pdfButton.isEnabled=enabled && capture!=null && !pdfExporting
    }

    override fun onSaveInstanceState(outState: Bundle) {
        outState.putInt("workspace_page",currentPage.ordinal)
        outState.putInt("diagnose_section",diagnoseSection)
        outState.putBoolean("cellular_input",cellularChoice.isChecked)
        outState.putBoolean("location_input",locationChoice.isChecked)
        choices.getOrNull(subscriptions.selectedItemPosition-1)?.subscriptionId?.let { outState.putInt("selected_subscription_id",it) }
        super.onSaveInstanceState(outState)
    }

    override fun onCreate(state:Bundle?) {
        setTheme(android.R.style.Theme_Material_NoActionBar)
        super.onCreate(state)
        location=PhoneLocation(this)
        window.statusBarColor=Color.parseColor("#07131f")
        window.navigationBarColor=Color.parseColor("#07131f")
        val shell=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setBackgroundColor(Color.parseColor("#07131f")) }
        setContentView(shell)
        SystemBarInsets.apply(shell)
        val header=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL;setPadding(dp(10),dp(4),dp(10),dp(4));setBackgroundColor(Color.parseColor("#0c1d2c")) }
        header.addView(ImageView(this).apply { setImageResource(R.drawable.ic_launcher_foreground);contentDescription=null },LinearLayout.LayoutParams(dp(38),dp(38)))
        val branding=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL }
        branding.addView(TextView(this).apply { text="VEILBREAKER";textSize=16f;letterSpacing=0.06f;setTypeface(null,Typeface.BOLD);setTextColor(Color.WHITE) })
        branding.addView(TextView(this).apply { text="MOBILE  /  0.8.22 DEV";textSize=10f;letterSpacing=0.04f;setTextColor(Color.parseColor("#62d5ee")) })
        header.addView(branding);shell.addView(header)
        val content=FrameLayout(this)
        shell.addView(content,LinearLayout.LayoutParams(-1,0,1f))
        fun text(parent:LinearLayout,value:String,size:Float=14f)=TextView(this).apply {
            text=value;textSize=size;setTextColor(Color.parseColor("#b8c9da"));setPadding(0,dp(4),0,dp(6));parent.addView(this)
        }
        fun page(title:String, description:String, scrollable:Boolean=true):LinearLayout {
            val body=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(12),dp(7),dp(12),dp(8)) }
            val screen: View = if(scrollable) ScrollView(this).apply { isFillViewport=true;addView(body) } else body
            content.addView(screen);pages.add(screen)
            text(body,title,19f).apply { setTypeface(null,Typeface.BOLD);setTextColor(Color.WHITE) }
            text(body,description,13f)
            return body
        }
        fun card(parent:LinearLayout,title:String):LinearLayout {
            val box=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;setPadding(dp(12),dp(10),dp(12),dp(12));background=GradientDrawable().apply { setColor(Color.parseColor("#102638"));setStroke(dp(1),Color.parseColor("#29495a"));cornerRadius=dp(10).toFloat() } }
            parent.addView(box,LinearLayout.LayoutParams(-1,-2).apply { topMargin=dp(10) })
            text(box,title,16f).apply { setTextColor(Color.parseColor("#63d6ee"));setTypeface(null,Typeface.BOLD) }
            return box
        }
        fun button(parent:LinearLayout,title:String,primary:Boolean=false,action:()->Unit)=Button(this).apply {
            text=title;isAllCaps=false;minHeight=dp(48);textSize=13f
            background=GradientDrawable().apply { setColor(Color.WHITE);cornerRadius=dp(9).toFloat() }
            backgroundTintList=buttonColors(if(primary) "#43d7e3" else "#233e51", "#1b2935")
            setTextColor(buttonColors(if(primary) "#06232a" else "#ffffff", "#8ca0ae"));elevation=0f;setOnClickListener { action() };parent.addView(this)
        }
        val live=page("Live", "Captured measurements and field equipment at a glance.")
        captureButton=button(live,"Capture on phone",true) { takeSnapshot(null) }
        status=text(live,"").apply {
            visibility=View.GONE
            addTextChangedListener(object:TextWatcher {
                override fun beforeTextChanged(s:CharSequence?,start:Int,count:Int,after:Int) {}
                override fun onTextChanged(s:CharSequence?,start:Int,before:Int,count:Int) { visibility=if(s.isNullOrBlank()) View.GONE else View.VISIBLE }
                override fun afterTextChanged(s:Editable?) {}
            })
        }
        inputReadiness=text(live,"Checking phone inputs…",12f)
        button(live,"Configure cellular & GPS") { showPage(WorkspacePage.DIAGNOSE);showDiagnoseSection(0) }
        liveDashboard=LiveDashboard(this,::openWifi,::openGps);live.addView(liveDashboard)

        val diagnose=page("Diagnose", "Choose an area to configure or test.",false)
        val segments=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL;setPadding(0,dp(3),0,dp(3)) }
        val segmentNames=listOf("Cellular","Wi-Fi","Network","Desktop","USB")
        segmentNames.forEachIndexed { index, name ->
            val tab=TextView(this).apply {
                text=name;textSize=11f;gravity=Gravity.CENTER;isClickable=true;isFocusable=true
                minimumHeight=dp(48);contentDescription="$name diagnostics"
                setOnClickListener { showDiagnoseSection(index) }
            }
            segments.addView(tab,LinearLayout.LayoutParams(0,-2,1f).apply { marginEnd=dp(3) });diagnoseTabs.add(tab)
        }
        diagnose.addView(segments)
        diagnoseScroll=ScrollView(this).apply { isFillViewport=true }
        val sectionRoot=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL }
        diagnoseScroll.addView(sectionRoot);diagnose.addView(diagnoseScroll,LinearLayout.LayoutParams(-1,0,1f))
        fun section():LinearLayout = LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;sectionRoot.addView(this);diagnoseSections.add(this) }
        val cellularSection=section()
        val inputs=card(cellularSection,"Phone inputs")
        cellularChoice=CheckBox(this).apply { text="Cellular measurements";textSize=14f;isChecked=true;inputs.addView(this) }
        locationChoice=CheckBox(this).apply { text="Record phone location (GPS)";textSize=14f;isChecked=false;inputs.addView(this) }
        text(inputs,"Location is optional. Coordinates are recorded only when enabled. No SIM is needed for location-only capture.")
        button(inputs,"Permissions and refresh SIMs") { if(allowed()) refresh() else requestPermissions(permissions,1) }
        subscriptions=Spinner(this);inputs.addView(subscriptions)
        cellularCaptureReadiness=text(inputs,"Checking phone inputs…",12f)
        text(inputs,"A capture saves a new snapshot as the latest phone evidence. Export an earlier capture first if you need to keep it.",12f)
        cellularCaptureButton=button(inputs,"Capture cellular evidence",true) { takeSnapshot(null) }
        cellularCaptureStatus=text(inputs,"")
        cellularReviewButton=button(inputs,"Review latest saved capture") { showPage(WorkspacePage.REPORTS) }
        status.addTextChangedListener(object:TextWatcher {
            override fun beforeTextChanged(s:CharSequence?,start:Int,count:Int,after:Int) {}
            override fun onTextChanged(s:CharSequence?,start:Int,before:Int,count:Int) {
                cellularCaptureStatus.text=s
                cellularCaptureStatus.visibility=if(s.isNullOrBlank()) View.GONE else View.VISIBLE
                if (::liveCellWorkspace.isInitialized) liveCellWorkspace.showCaptureStatus(s)
            }
            override fun afterTextChanged(s:Editable?) {}
        })
        cellularCaptureStatus.visibility=View.GONE
        cellConnectionWorkspace=CellConnectionWorkspace(this) { choices.getOrNull(subscriptions.selectedItemPosition-1)?.subscriptionId }
        cellularSection.addView(cellConnectionWorkspace)
        liveCellWorkspace=LiveCellWorkspace(this, { choices.getOrNull(subscriptions.selectedItemPosition-1)?.subscriptionId },
            { externalActionsEnabled() && cellularChoice.isChecked }, { channelPlan },
            { takeSnapshot(null) }, { showPage(WorkspacePage.REPORTS) })
        cellularSection.addView(liveCellWorkspace)
        val wifiSection=section()
        val wifi=card(wifiSection,"Wi-Fi environment")
        text(wifi,"Inspect connected and cached nearby networks. Stop a Desktop session before opening.")
        wifiButton=button(wifi,"Inspect Wi-Fi") { openWifi() }
        val networkSection=section()
        networkTestWorkspace=NetworkTestWorkspace(this);networkSection.addView(networkTestWorkspace)
        networkSection.addView(NetworkInventoryWorkspace(this))
        val desktopSection=section()
        val connect=card(desktopSection,"Desktop connection")
        button(connect,"Connect to Veilbreaker",true) { armUsb() }
        usbStatus=text(connect,"Disconnected · USB cable and debugging approval required. No code needs to be typed.")
        button(connect,"Stop and disconnect") { stopUsb();cancelPending() }
        val hardwareSection=section()
        hardwareSection.addView(UsbHardwareWorkspace(this))

        val survey=page("Survey", "Organize field captures and inspect GPS positions.",false)
        gpsButton=button(survey,"Open GPS & map") { openGps() }
        surveyWorkspace=SurveyWorkspace(this, { capture }, { complete -> takeSnapshot(null, complete) },
            { if(pending && connection==null) cancelPending() })
        survey.addView(surveyWorkspace,LinearLayout.LayoutParams(-1,0,1f))

        val reports=page("Reports", "Review and export the latest saved phone capture.")
        val local=card(reports,"Captured evidence")
        reportSummary=text(local,"No saved capture.")
        lateinit var browseCells: Button
        browseCells=button(local,"Browse captured cells") {
            val opening=cellInventory.visibility!=View.VISIBLE
            cellInventory.visibility=if(opening) View.VISIBLE else View.GONE
            browseCells.text=if(opening) "Hide captured cells" else "Browse captured cells"
        }
        cellInventory=CellInventoryWorkspace(this).apply { visibility=View.GONE };local.addView(cellInventory)
        pdfButton=button(local,"Export PDF…",true) {
            capture?.let {
                exportPdfText=it.toString()
                startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE);type="application/pdf";putExtra(Intent.EXTRA_TITLE,"veilbreaker-field-report.pdf")
                },3)
            }
        }
        exportButton=button(local,"Export capture JSON…") {
            capture?.let {
                exportText=it.toString(2)
                startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                    addCategory(Intent.CATEGORY_OPENABLE);type="application/json";putExtra(Intent.EXTRA_TITLE,"veilbreaker-"+it.getString("capture_id")+".json")
                },2)
            }
        }
        detailsButton=button(local,"Show cellular details") { previewMode=if(previewMode=="details") "summary" else "details";showCapture() }
        rawButton=button(local,"Show raw JSON") { previewMode=if(previewMode=="raw") "summary" else "raw";showCapture() }
        reportStatus=text(local,"The last saved capture is kept on this phone.")
        preview=text(local,"No saved capture.")
        cellularVisuals=CellularVisuals(this);local.addView(cellularVisuals)
        val tools=page("Tools", "Calculators, field references, planning and optional online lookup.")
        val toolsTabs=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL;setPadding(0,dp(4),0,dp(4)) }
        val names=listOf("Calculate", "References", "Planning", "Online")
        val tabs=names.map { name -> TextView(this).apply { text=name;textSize=12f;gravity=Gravity.CENTER;minimumHeight=dp(48);isClickable=true;isFocusable=true;contentDescription="$name tools" } }
        tabs.forEach { toolsTabs.addView(it,LinearLayout.LayoutParams(0,-2,1f)) }
        tools.addView(toolsTabs)
        val calculatorWorkspace=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            addView(EngineeringToolsWorkspace(this@MainActivity))
            val converters=WirelessToolsWorkspace(this@MainActivity).apply { visibility=View.GONE }
            lateinit var converterToggle:Button
            converterToggle=button(this,"Show two-way Wi-Fi and power converters") {
                val show=converters.visibility==View.GONE
                converters.visibility=if(show) View.VISIBLE else View.GONE
                converterToggle.text=if(show) "Hide two-way converters" else "Show two-way Wi-Fi and power converters"
            }
            addView(converters)
        }
        val planningWorkspace=PlanningModelsWorkspace(this) { capture }
        lateinit var showTools:(Int)->Unit
        val onlineWorkspace=OnlineLookupWorkspace(this, onUseCandidate = { candidate ->
            AlertDialog.Builder(this).setTitle("Use OpenCellID candidate in FWA planning?")
                .setMessage("This replaces the candidate-site coordinates in the current FWA form. Antenna coordinates and frequency are unchanged. OpenCellID is a community-derived estimate, not a verified tower or line-of-sight result.")
                .setPositiveButton("Use candidate") { _,_ ->
                    planningWorkspace.useOpenCellCandidate(candidate)
                    showTools(2)
                    tools.post { (tools.parent as? ScrollView)?.smoothScrollTo(0,0) }
                }.setNegativeButton("Cancel", null).show()
        }, captureProvider = { capture })
        val workspaces=listOf(calculatorWorkspace,WirelessReferenceWorkspace(this),planningWorkspace,onlineWorkspace)
        workspaces.forEach { tools.addView(it) }
        showTools = { selected ->
            workspaces.forEachIndexed { i, workspace -> workspace.visibility=if(i==selected) View.VISIBLE else View.GONE }
            tabs.forEachIndexed { i, tab ->
                tab.background=background(if(i==selected) "#2179ce" else "#1b3042")
                tab.setTextColor(Color.WHITE);tab.isSelected=i==selected
            }
        }
        tabs.forEachIndexed { i, tab -> tab.setOnClickListener { showTools(i) } };showTools(0)
        val bar=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL;setPadding(dp(4),dp(4),dp(4),dp(4));setBackgroundColor(Color.parseColor("#0a1b29")) }
        val labels=listOf("Live","Diagnose","Survey","Reports","Tools")
        val icons=listOf(R.drawable.ic_nav_live,R.drawable.ic_nav_diagnose,R.drawable.ic_nav_survey,R.drawable.ic_nav_reports,R.drawable.ic_nav_tools)
        WorkspacePage.entries.forEachIndexed { index, page ->
            val item=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL;gravity=Gravity.CENTER;isClickable=true;isFocusable=true;contentDescription=labels[index];minimumHeight=dp(54);setOnClickListener { showPage(page) } }
            val icon=ImageView(this).apply { setImageResource(icons[index]);contentDescription=null }
            val caption=TextView(this).apply { text=labels[index];textSize=11f;gravity=Gravity.CENTER }
            item.addView(icon,LinearLayout.LayoutParams(dp(21),dp(21)));item.addView(caption)
            bar.addView(item,LinearLayout.LayoutParams(0,-2,1f));navItems.add(item);navLabels.add(caption);navIcons.add(icon)
        }
        shell.addView(bar)
        if(state!=null) {
            cellularChoice.isChecked=state.getBoolean("cellular_input",true)
            locationChoice.isChecked=state.getBoolean("location_input",false)
        }
        cellularChoice.setOnCheckedChangeListener { _,_->refresh() }
        locationChoice.setOnCheckedChangeListener { _,_->refresh() }
        subscriptions.onItemSelectedListener=object:android.widget.AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent:android.widget.AdapterView<*>?, view:View?, position:Int, id:Long) { cellConnectionWorkspace.selectionChanged();liveCellWorkspace.selectionChanged();updateCaptureReadiness() }
            override fun onNothingSelected(parent:android.widget.AdapterView<*>?) { cellConnectionWorkspace.selectionChanged();liveCellWorkspace.selectionChanged();updateCaptureReadiness() }
        }
        capture=try { JSONObject(AtomicFile(filesDir.resolve("last-capture.json")).openRead().bufferedReader().use { it.readText() }) } catch(_:Exception) { null }
        showCapture();refresh()
        if(state?.containsKey("selected_subscription_id")==true) {
            subscriptions.setSelection(SimSelection.spinnerPosition(choices.map { it.subscriptionId },state.getInt("selected_subscription_id")))
            updateCaptureReadiness()
        }
        showDiagnoseSection((state?.getInt("diagnose_section",0) ?: 0).coerceIn(0,4));showPage(WorkspaceNavigation.restore(state?.getInt("workspace_page",0) ?: 0))
    }
    private fun allowed() = (!cellularChoice.isChecked || (checkSelfPermission(Manifest.permission.READ_PHONE_STATE)==PackageManager.PERMISSION_GRANTED && checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED)) &&
        (!locationChoice.isChecked || checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED)
    private fun refresh() {
        if(connection!=null) return
        val selectedId=choices.getOrNull(subscriptions.selectedItemPosition-1)?.subscriptionId
        choices=try { if(checkSelfPermission(Manifest.permission.READ_PHONE_STATE)==PackageManager.PERMISSION_GRANTED) getSystemService(SubscriptionManager::class.java).activeSubscriptionInfoList ?: emptyList() else emptyList() } catch(_:SecurityException) { emptyList() }
        subscriptions.adapter=ArrayAdapter(this,android.R.layout.simple_spinner_dropdown_item,listOf("Choose a SIM")+choices.map { "SIM ${it.simSlotIndex+1} · ${it.displayName}" })
        subscriptions.setSelection(SimSelection.spinnerPosition(choices.map { it.subscriptionId },selectedId))
        subscriptions.isEnabled=cellularChoice.isChecked
        updateCaptureReadiness()
        syncExternalActions()
    }
    private fun updateCaptureReadiness() {
        if (!::inputReadiness.isInitialized || !::subscriptions.isInitialized) return
        val noInput=!cellularChoice.isChecked && !locationChoice.isChecked
        val missingSim=cellularChoice.isChecked && choices.getOrNull(subscriptions.selectedItemPosition-1)==null
        inputReadiness.text=when {
            connection!=null -> "Desktop session active."
            pending -> "Capture in progress."
            noInput -> "Choose cellular or GPS in Configure inputs."
            !allowed() -> "Grant the required phone permissions in Configure inputs."
            missingSim -> "Choose a SIM in Configure inputs before capturing cellular data."
            else -> "Inputs ready for capture."
        }
        captureButton.isEnabled=connection==null && !pending && !noInput && allowed() && !missingSim
        if (::cellularCaptureButton.isInitialized) {
            cellularCaptureButton.isEnabled=captureButton.isEnabled && cellularChoice.isChecked
            cellularCaptureReadiness.text=if (!cellularChoice.isChecked) "Enable cellular measurements to capture cellular evidence." else inputReadiness.text
            if (::liveCellWorkspace.isInitialized) liveCellWorkspace.setSnapshotReady(cellularCaptureButton.isEnabled, cellularCaptureReadiness.text)
        }
    }
    override fun onRequestPermissionsResult(code:Int,p:Array<out String>,results:IntArray) { super.onRequestPermissionsResult(code,p,results);if(code==1) { refresh();liveDashboard.refreshWifi() } }
    private fun takeSnapshot(target:UsbSession?, onComplete: ((Result<JSONObject>) -> Unit)? = null) {
        fun reject(message: String) { status.text=message; onComplete?.invoke(Result.failure(IllegalStateException(message))) }
        if(pending) { reject("A capture is already in progress."); return }
        if(target==null && connection!=null) { reject("Stop the Desktop session before capturing on the phone."); return }
        val useCell=connection?.cellular ?: cellularChoice.isChecked
        val useLocation=connection?.location ?: locationChoice.isChecked
        if(!allowed()) { target?.finish("partial");reject("Permission unavailable. Stop and grant permissions again.");return }
        val selected=choices.getOrNull(subscriptions.selectedItemPosition-1)
        if(useCell && selected==null) { target?.finish("partial");reject("Choose a SIM for cellular measurements.");return }
        if(!useCell && !useLocation) { reject("Choose at least one input.");return }
        if(target==null) try { location.start(useLocation) } catch(_:RuntimeException) { reject("Location service unavailable. Previous evidence is retained.");return }
        pendingSnapshotCompletion=onComplete
        val epoch=++generation;pending=true;lockInputs(true)
        val started=Instant.now().toString()
        val locationDeadline=SystemClock.elapsedRealtime()+30000
        var cellResponseUtc:String?=null
        status.text=if(useCell) "Collecting cellular measurements…" else "Collecting location…"
        fun finish(cells:List<CellInfo>?,error:String?) {
            if(epoch!=generation || !pending || (target!=null && target!==connection?.session)) return
            pending=false
            val elapsed=SystemClock.elapsedRealtime()
            var result:Result<JSONObject>?=null
            try {
                val stillPresent=!useCell || getSystemService(SubscriptionManager::class.java).activeSubscriptionInfoList?.any { it.subscriptionId==selected!!.subscriptionId }==true
                val source=if(stillPresent) cells.orEmpty() else emptyList()
                val locationValue=if(useLocation) location.atReceipt(elapsed) else null
                val assessment=CaptureAssessment.assess(useCell,source.size,stillPresent,error,useLocation,locationValue?.optString("status"))
                val outcome=assessment.outcome
                val notes=assessment.notes.toMutableList()
                if(useLocation && cellResponseUtc!=null) notes.add("Cell response and phone location were acquired separately; their timestamps may differ.")
                val snapshot=CaptureSerializer.envelope(Build.MANUFACTURER,Build.MODEL,Build.VERSION.RELEASE,Build.VERSION.SDK_INT,"0.8.22-dev",
                    source.take(256).map { CellularSnapshot.cell(it,elapsed) },elapsed,outcome,notes,started)
                val observation=snapshot.getJSONArray("observations").getJSONObject(0)
                cellResponseUtc?.let { observation.put("cell_response_received_utc",it) }
                snapshot.getJSONObject("collection").put("inputs",JSONObject().put("cellular",useCell).put("location",useLocation))
                if(locationValue!=null) observation.put("location",locationValue)
                if(useCell) {
                    val manager=getSystemService(TelephonyManager::class.java).createForSubscriptionId(selected!!.subscriptionId)
                    snapshot.getJSONArray("subscriptions").getJSONObject(0).put("network_operator",manager.networkOperatorName).put("sim_carrier",selected.carrierName?.toString() ?: "")
                } else {
                    snapshot.getJSONArray("subscriptions").getJSONObject(0).put("key","location-only").put("kind","location_only")
                    observation.put("subscription_key","location-only")
                }
                if(target!=null) { target.accept(snapshot);if(!stillPresent || !allowed()) target.finish("partial") }
                else { save(snapshot);result=Result.success(snapshot) }
                val loc=observation.optJSONObject("location")
                val prefix=if(outcome=="partial") "Partial capture saved" else "Capture saved"
                status.text=if(loc==null) "$prefix · location off" else "$prefix · " + LocationEvidence.describeCaptured(loc)
            } catch(_:Exception) { target?.finish("partial");status.text="Capture unavailable. Previous evidence is retained.";result=Result.failure(IllegalStateException("Capture unavailable. Previous evidence is retained.")) }
            if(target==null) location.stop()
            lockInputs(connection!=null);showCapture()
            if(target==null) finishSnapshotRequest(result ?: Result.failure(IllegalStateException("Capture unavailable.")))
        }
        if(!useCell) {
            val waitForFix=object:Runnable {
                override fun run() {
                    if(epoch!=generation || !pending) return
                    val now=SystemClock.elapsedRealtime()
                    val state=location.atReceipt(now).optString("status")
                    if(!CaptureWaitPolicy.waitForLocation(target==null,useLocation,state,now,locationDeadline)) finish(emptyList(),null)
                    else { status.text="Waiting for GPS fix… Keep the phone near a clear view of the sky.";handler.postDelayed(this,1000) }
                }
            }
            handler.postDelayed(waitForFix,1000);return
        }
        var cellResponseReceived=false
        lateinit var cellTimeout:Runnable
        fun cellularComplete(cells:List<CellInfo>?,error:String?) {
            if(epoch!=generation || !pending || cellResponseReceived || (target!=null && target!==connection?.session)) return
            cellResponseReceived=true;handler.removeCallbacks(cellTimeout)
            if(error==null && cells!=null) cellResponseUtc=Instant.now().toString()
            val waitForFix=object:Runnable {
                override fun run() {
                    if(epoch!=generation || !pending) return
                    val now=SystemClock.elapsedRealtime()
                    val state=if(useLocation) location.atReceipt(now).optString("status") else null
                    if(CaptureWaitPolicy.waitForLocation(target==null,useLocation,state,now,locationDeadline)) {
                        status.text="Cell response received · waiting for GPS fix (up to 30 seconds total)…"
                        handler.postDelayed(this,1000)
                    } else finish(cells,error)
                }
            }
            waitForFix.run()
        }
        cellTimeout=Runnable { cellularComplete(null,"Cell request timed out") }
        handler.postDelayed(cellTimeout,15000)
        try {
            getSystemService(TelephonyManager::class.java).createForSubscriptionId(selected!!.subscriptionId).requestCellInfoUpdate(mainExecutor,object:TelephonyManager.CellInfoCallback() {
                override fun onCellInfo(info:MutableList<CellInfo>) { cellularComplete(info,null) }
                override fun onError(code:Int,detail:Throwable?) { cellularComplete(null,"Cell information unavailable") }
            })
        } catch(_:Exception) { cellularComplete(null,"Cell information unavailable") }
    }
    private fun save(value:JSONObject) {
        val file=AtomicFile(filesDir.resolve("last-capture.json"))
        val stream=file.startWrite()
        try { stream.write(value.toString().toByteArray(Charsets.UTF_8));file.finishWrite(stream) }
        catch(error:Exception) { file.failWrite(stream);throw error }
        capture=value
    }
    private fun finishSnapshotRequest(result:Result<JSONObject>) {
        val completion=pendingSnapshotCompletion;pendingSnapshotCompletion=null;completion?.invoke(result)
    }
    private fun showCapture() {
        val value=capture
        if (::cellularReviewButton.isInitialized) cellularReviewButton.isEnabled=value!=null
        if (::liveCellWorkspace.isInitialized) liveCellWorkspace.setCaptureAvailable(value!=null)
        cellularVisuals.showCapture(value,if(value==null) null else channelPlan)
        cellInventory.showCapture(value,if(value==null) null else channelPlan)
        liveDashboard.showCapture(value,if(value==null) null else channelPlan)
        reportSummary.text=if(value==null) "No saved capture. Capture on the phone to create a report." else {
            val observations=value.getJSONArray("observations")
            val model=LiveOverviewModel.build(value,channelPlan)
            val lines=mutableListOf("${observations.length()} observations · ${value.getJSONObject("collection").optString("outcome")}",
                "Captured ${value.optString("created_utc","Time unavailable")}")
            for(cell in model.cells.take(2)) {
                val metrics=cell.values.joinToString(" · ") { metric ->
                    "${metric.label}: " + (metric.value?.let { "${it} ${metric.unit}" } ?: "Not exposed")
                }
                lines.add("${cell.title} · ${cell.band}\n$metrics")
            }
            if(model.cells.isEmpty()) lines.add("No registered LTE/NR cell reported.")
            model.gps?.let(lines::add)
            lines.joinToString("\n")
        }
        preview.text=if(value==null || previewMode=="summary") "" else if(previewMode=="raw") {
            val rawText=value.toString(2)
            rawText.take(20000)+if(rawText.length>20000) "\n[Preview truncated; export retains the complete capture.]" else ""
        } else {
            val details=CellularOverview.render(value,channelPlan)
            details.take(40000)+if(details.length>40000) "\n[Preview truncated; export retains the complete capture.]" else ""
        }
        preview.visibility=if(value==null || previewMode=="summary") View.GONE else View.VISIBLE
        detailsButton.text=if(previewMode=="details") "Hide cellular details" else "Show cellular details"
        rawButton.text=if(previewMode=="raw") "Hide raw JSON" else "Show raw JSON"
        detailsButton.isEnabled=value!=null;rawButton.isEnabled=value!=null
        syncExternalActions()
    }
    private fun lockInputs(locked:Boolean) { cellularChoice.isEnabled=!locked;locationChoice.isEnabled=!locked;subscriptions.isEnabled=!locked && cellularChoice.isChecked;updateCaptureReadiness();syncExternalActions() }
    private fun cancelPending() { generation++;pending=false;location.stop();lockInputs(connection!=null);showCapture();finishSnapshotRequest(Result.failure(IllegalStateException("Capture cancelled; previous evidence is retained."))) }
    private fun armUsb() {
        if(pending || connection!=null || !allowed() || (!cellularChoice.isChecked && !locationChoice.isChecked) || (cellularChoice.isChecked && subscriptions.selectedItemPosition<1)) { usbStatus.text="Choose inputs, grant permissions, and select a SIM if using cellular.";return }
        val conn=UsbConnection({SystemClock.elapsedRealtime()},cellularChoice.isChecked,locationChoice.isChecked,{session->takeSnapshot(session)},{save(it);showCapture()},
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
        } catch(_:Exception) { stopUsb();usbStatus.text="USB endpoint unavailable. Stop another companion and retry." }
    }
    private fun stopUsb() { endpoint?.close();endpoint=null;connection?.revoke();connection=null;location.stop();usbStatus.text="Disconnected · reconnect for another survey.";window.clearFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) }
    override fun onStop() { liveCellWorkspace.stop();networkTestWorkspace.cancel();stopUsb();cancelPending();super.onStop() }
    @Deprecated("Platform result keeps companion dependency-light")
    override fun onActivityResult(request:Int,result:Int,data:Intent?) {
        super.onActivityResult(request,result,data)
        if(surveyWorkspace.onActivityResult(request,result,data)) return
        if(request==2 && result==RESULT_OK && data?.data!=null) try {
            contentResolver.openOutputStream(data.data!!,"wt")?.use { it.write((exportText ?: error("No export")).toByteArray(Charsets.UTF_8)) } ?: error("Cannot export")
            reportStatus.text="Capture exported."
        } catch(_:Exception) { reportStatus.text="Export failed. Saved capture remains available." }
        if(request==2) exportText=null
        if(request==3) {
            val saved=exportPdfText;exportPdfText=null
            val uri=data?.data
            if(result==RESULT_OK && uri!=null && saved!=null) {
                val plan=channelPlan.toString()
                val resolver=applicationContext.contentResolver
                pdfExporting=true;syncExternalActions();reportStatus.text="Preparing PDF…"
                Thread {
                    val resultPdf=runCatching {
                        resolver.openOutputStream(uri,"wt")?.use { output ->
                            CaptureReportPdf.write(JSONObject(saved),JSONObject(plan),output)
                        } ?: error("Cannot open destination")
                    }
                    handler.post {
                        if(!isFinishing && !isDestroyed) {
                            pdfExporting=false;syncExternalActions()
                            reportStatus.text=if(resultPdf.isSuccess) "PDF report exported." else "PDF export failed. Saved capture remains available."
                        }
                    }
                }.apply { name="Veilbreaker PDF export";start() }
            } else if(result==RESULT_OK) reportStatus.text="PDF export unavailable. Try again from the saved capture."
        }
    }
}
