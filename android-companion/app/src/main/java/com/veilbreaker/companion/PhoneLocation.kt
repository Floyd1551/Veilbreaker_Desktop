package com.veilbreaker.companion

import android.content.Context
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Bundle
import android.os.Looper
import org.json.JSONObject

/** Foreground capture only; no last-known fix is silently substituted. */
class PhoneLocation(context: Context) {
    private val manager = context.getSystemService(LocationManager::class.java)
    private var latest: Location? = null
    private var listener: LocationListener? = null
    private var generation = 0
    private var state = "disabled"
    fun start(enabled: Boolean) {
        stop(); latest = null
        if (!enabled) return
        if (!manager.isLocationEnabled) { state="disabled"; return }
        state="unavailable"
        val epoch = generation
        val callback = object: LocationListener {
            override fun onLocationChanged(location: Location) { if (generation==epoch) latest=Location(location) }
            override fun onProviderEnabled(provider: String) { }
            override fun onProviderDisabled(provider: String) { if (generation==epoch) { latest=null; state="disabled" } }
            @Deprecated("Platform callback") override fun onStatusChanged(provider: String?, status: Int, extras: Bundle?) { }
        }
        listener=callback
        try {
            if (!manager.isProviderEnabled(LocationManager.GPS_PROVIDER)) { state="disabled"; return }
            manager.requestLocationUpdates(LocationManager.GPS_PROVIDER,1000L,0f,callback,Looper.getMainLooper())
        } catch (_: SecurityException) { state="permission_denied" }
    }
    fun stop() {
        generation++
        try { listener?.let { manager.removeUpdates(it) } } catch (_: SecurityException) { }
        listener=null; latest=null; state="disabled"
    }
    fun atReceipt(elapsed: Long): JSONObject {
        val fix=latest ?: return LocationEvidence.unavailable(state)
        val result=LocationEvidence.fix(fix.latitude,fix.longitude,if(fix.hasAccuracy()) fix.accuracy.toDouble() else null,
            fix.time,fix.elapsedRealtimeNanos/1000000,elapsed,fix.provider ?: "gnss",fix.isFromMockProvider)
        return LocationEvidence.addOptional(result, if(fix.hasAltitude()) fix.altitude else null,
            if(fix.hasVerticalAccuracy()) fix.verticalAccuracyMeters.toDouble() else null,
            if(fix.hasSpeed()) fix.speed.toDouble() else null,
            if(fix.hasBearing()) fix.bearing.toDouble() else null)
    }
}
