package com.veilbreaker.companion

import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.net.ConnectivityManager
import android.net.Network
import android.net.NetworkCapabilities
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.text.InputType
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import java.io.InterruptedIOException
import java.net.URI
import java.net.UnknownHostException
import java.util.Locale
import javax.net.ssl.HttpsURLConnection
import javax.net.ssl.SSLException

/** Explicit, bounded foreground HTTPS test on one chosen Android transport. */
class NetworkTestWorkspace(context: Context) : LinearLayout(context) {
    private class Job {
        @Volatile var cancelled = false
        @Volatile var connection: HttpsURLConnection? = null
        var thread: Thread? = null
    }

    private data class Result(val title: String, val details: String)

    private val handler = Handler(Looper.getMainLooper())
    private var current: Job? = null
    private var running: Job? = null
    private var timeout: Runnable? = null
    private val transport: Spinner
    private val address: EditText
    private val run: Button
    private val stop: Button
    private val status: TextView
    private val results: TextView
    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    init {
        orientation = VERTICAL
        setPadding(dp(14), dp(12), dp(14), dp(14))
        background = android.graphics.drawable.GradientDrawable().apply {
            setColor(Color.parseColor("#111d2a")); setStroke(dp(1), Color.parseColor("#2a4051")); cornerRadius = dp(8).toFloat()
        }
        fun label(value: String, size: Float = 13f, bold: Boolean = false) = TextView(context).apply {
            text = value; textSize = size; setTextColor(Color.parseColor(if (bold) "#ecf5fa" else "#b8cbd9"))
            setPadding(0, dp(5), 0, dp(5)); if (bold) setTypeface(null, Typeface.BOLD)
            this@NetworkTestWorkspace.addView(this)
        }
        fun button(value: String, primary: Boolean = false) = Button(context).apply {
            text = value; isAllCaps = false; minHeight = dp(48)
            backgroundTintList = ColorStateList.valueOf(Color.parseColor(if (primary) "#3277dc" else "#243b50"))
            setTextColor(Color.WHITE); this@NetworkTestWorkspace.addView(this)
        }
        label("NETWORK TEST", 16f, true)
        label("Choose a transport and enter a trusted HTTPS download URL. A request is made only when you run the test.")
        transport = Spinner(context).apply {
            adapter = ArrayAdapter(context, android.R.layout.simple_spinner_dropdown_item, listOf("Choose transport", "Cellular", "Wi-Fi"))
            contentDescription = "Network test transport"; this@NetworkTestWorkspace.addView(this)
        }
        address = EditText(context).apply {
            hint = "https://your-server.example/test-file"; contentDescription = "HTTPS test URL"
            setSingleLine(true); setTextColor(Color.WHITE); setHintTextColor(Color.LTGRAY)
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_URI
            filters = arrayOf(android.text.InputFilter.LengthFilter(2048)); this@NetworkTestWorkspace.addView(this)
        }
        label("Receives at most 2 MiB; the test stops after a short time. No upload, jitter or packet-loss test is performed.", 12f)
        run = button("Run test", true).apply { setOnClickListener { start() } }
        stop = button("Cancel test").apply { isEnabled = false; setOnClickListener { cancel() } }
        status = label("Ready · no network request has been made.")
        results = label("Connection, response and download measurements will appear here.")
    }

    private fun selectNetwork(): Pair<Network, String> {
        val manager = context.getSystemService(ConnectivityManager::class.java)
            ?: throw IllegalArgumentException("Network service unavailable.")
        val type = when (transport.selectedItemPosition) {
            1 -> NetworkCapabilities.TRANSPORT_CELLULAR
            2 -> NetworkCapabilities.TRANSPORT_WIFI
            else -> throw IllegalArgumentException("Choose cellular or Wi-Fi.")
        }
        val label = if (type == NetworkCapabilities.TRANSPORT_CELLULAR) "Cellular" else "Wi-Fi"
        val networks = try {
            manager.allNetworks.filter { network ->
                val caps = manager.getNetworkCapabilities(network)
                caps?.hasTransport(type) == true && caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
            }
        } catch (_: SecurityException) { throw IllegalArgumentException("Android did not permit network inspection.") }
        require(networks.isNotEmpty()) { "$label network unavailable. Connect that transport and try again." }
        require(networks.size == 1) { "Multiple $label networks are available. Disconnect extras before testing." }
        return Pair(networks.single(), label)
    }

    private fun start() {
        if (running?.thread?.isAlive == true) { status.text = "Previous network operation is still stopping."; return }
        val uri: URI
        val selected: Pair<Network, String>
        try { uri = NetworkTestRules.target(address.text.toString()); selected = selectNetwork() }
        catch (e: IllegalArgumentException) { status.text = e.message ?: "Check the test settings."; return }
        val job = Job(); current = job; running = job
        run.isEnabled = false; stop.isEnabled = true; transport.isEnabled = false; address.isEnabled = false
        status.text = "Testing ${selected.second} · one HTTPS request to ${uri.host}."
        results.text = "Waiting for response…"
        val expiry = Runnable { if (current === job) cancelJob(job, "Time limit reached; waiting for the network operation to stop.") }
        timeout = expiry; handler.postDelayed(expiry, 15_000)
        job.thread = Thread {
            val result = try { execute(job, selected.first, selected.second, uri) }
                catch (_: UnknownHostException) { Result("Test failed", "The selected network could not resolve the server.") }
                catch (_: SSLException) { Result("Test failed", "TLS verification failed. Use a trusted HTTPS server.") }
                catch (_: InterruptedIOException) { Result("Test timed out", "The selected network did not respond before the timeout.") }
                catch (_: Exception) { Result("Test failed", "The selected network could not complete the HTTPS request.") }
            finally { try { job.connection?.disconnect() } catch (_: Exception) { }; job.connection = null }
            handler.post {
                if (running === job) running = null
                if (current === job && !job.cancelled) {
                    timeout?.let(handler::removeCallbacks); timeout = null; current = null
                    status.text = result.title; results.text = result.details
                }
                if (current == null) { run.isEnabled = true; stop.isEnabled = false; transport.isEnabled = true; address.isEnabled = true }
            }
        }.apply { name = "Veilbreaker network test"; isDaemon = true; start() }
    }

    private fun execute(job: Job, network: Network, transport: String, uri: URI): Result {
        val started = SystemClock.elapsedRealtime()
        val connection = network.openConnection(uri.toURL()) as? HttpsURLConnection
            ?: throw IllegalArgumentException("HTTPS required.")
        job.connection = connection
        if (job.cancelled) throw InterruptedIOException()
        connection.instanceFollowRedirects = false
        connection.connectTimeout = 5000; connection.readTimeout = 2500
        connection.useCaches = false; connection.requestMethod = "GET"
        connection.setRequestProperty("Accept-Encoding", "identity")
        connection.connect()
        val connectMs = (SystemClock.elapsedRealtime() - started).coerceAtLeast(0)
        if (job.cancelled) throw InterruptedIOException()
        val code = connection.responseCode
        val headersMs = (SystemClock.elapsedRealtime() - started).coerceAtLeast(0)
        if (code !in 200..299) return Result("Test stopped · HTTP $code", "$transport transport · no redirects followed. No download measurement was made.")
        val dataStart = SystemClock.elapsedRealtime()
        val deadline = started + 10_000
        val limit = 2 * 1024 * 1024L
        var bytes = 0L
        var reason = "Response ended"
        connection.inputStream.use { input ->
            val buffer = ByteArray(16 * 1024)
            while (bytes < limit) {
                if (job.cancelled || Thread.currentThread().isInterrupted) throw InterruptedIOException()
                if (SystemClock.elapsedRealtime() >= deadline) { reason = "Time limit reached; response may be partial"; break }
                val count = try { input.read(buffer, 0, minOf(buffer.size.toLong(), limit - bytes).toInt()) }
                    catch (e: InterruptedIOException) { if (bytes == 0L || job.cancelled) throw e; reason = "Read timed out; response is partial"; break }
                if (count < 0) break
                if (count == 0) continue
                bytes += count
            }
        }
        val elapsed = (SystemClock.elapsedRealtime() - dataStart).coerceAtLeast(0)
        if (bytes >= limit) reason = "2 MiB limit reached; response may be partial"
        val rate = NetworkTestRules.mbps(bytes, elapsed)?.let { String.format(Locale.US, "%.2f Mbps", it) }
            ?: "Not shown: transfer was too short or too small"
        return Result("Test complete · HTTP $code", "$transport network\nConnection setup: $connectMs ms\nResponse headers: $headersMs ms from start\nReceived: $bytes bytes in $elapsed ms\nDownload during transfer: $rate\n$reason. Speed is an estimate for this transfer, not a sustained capacity or guarantee.\nUpload, jitter and packet loss: not measured.")
    }

    private fun cancelJob(job: Job, message: String) {
        if (current !== job) return
        current = null; job.cancelled = true
        timeout?.let(handler::removeCallbacks); timeout = null
        job.thread?.interrupt()
        val connection = job.connection
        if (connection != null) Thread { try { connection.disconnect() } catch (_: Exception) { } }
            .apply { name = "Veilbreaker test cancellation"; isDaemon = true; start() }
        status.text = message; stop.isEnabled = false
    }

    /** Called on the UI thread when the user leaves Diagnose or the app. */
    fun cancel() { current?.let { cancelJob(it, "Test cancelled; waiting for the network operation to stop.") } }
    override fun onDetachedFromWindow() { cancel(); super.onDetachedFromWindow() }
    override fun onWindowVisibilityChanged(visibility: Int) { super.onWindowVisibilityChanged(visibility); if (visibility != View.VISIBLE) cancel() }
    override fun onVisibilityChanged(changedView: View, visibility: Int) { super.onVisibilityChanged(changedView, visibility); if (visibility != View.VISIBLE) cancel() }
}
