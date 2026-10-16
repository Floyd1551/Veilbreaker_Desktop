package com.veilbreaker.companion

import org.json.JSONObject
import java.security.MessageDigest
import java.util.UUID

/** Approval lifetime is independent of each bounded capture. Main-thread only. */
class UsbConnection(private val now: () -> Long, val cellular: Boolean, val location: Boolean,
    private val sample: (UsbSession) -> Unit, private val save: (JSONObject) -> Unit,
    private val begin: () -> Unit, private val end: () -> Unit) {
    val token=UUID.randomUUID().toString().replace("-","")
    val id=UUID.randomUUID().toString()
    var session: UsbSession? = null; private set
    var reusable=false
    private var born=now()
    private var idle=now()
    private var revoked=false
    private var finished=true
    private val used=mutableSetOf<String>()
    fun capabilities()=JSONObject().put("reusable_sessions",true).put("location",true)
        .put("cellular_enabled",cellular).put("location_enabled",location)
    fun approve(survey: Boolean) { reusable=survey; born=now(); idle=now() }
    fun expire() {
        session?.expire()
        if (session?.terminal()==true && !finished) { finished=true; idle=now(); end() }
        if(now()-born>=3600000 || (finished && now()-idle>=900000)) revoke()
    }
    fun revoke() { revoked=true; session?.finish("cancelled"); end() }
    fun command(name: String, supplied: String, body: JSONObject): JSONObject {
        require(MessageDigest.isEqual(token.toByteArray(),supplied.toByteArray())) { "Authorization required" }
        expire(); require(!revoked) { "Connection expired; reconnect on phone" }
        val request=body.getString("request_id")
        require(request.length in 1..64 && used.size<10000 && used.add(request)) { "Duplicate request" }
        if(name=="disconnect") { revoke(); return JSONObject().put("protocol",1).put("request_id",request).put("session_id",id).put("status","cancelled") }
        if(name=="start") {
            require(session==null || (reusable && session!!.terminal())) { "Capture already used or active" }
            require(body.optBoolean("cellular",true)==cellular && body.optBoolean("location",false)==location) { "Selected phone inputs differ; reconnect" }
            val duration=body.getInt("duration_s"); require(duration in 5..300)
            lateinit var next: UsbSession
            next=UsbSession(now,{ sample(next) },save)
            session=next; finished=false; begin()
        }
        val active=session ?: throw IllegalArgumentException("Start capture first")
        val response=active.command(name,active.token,body)
        expire()
        return response.put("connection_id",id).put("capabilities",capabilities())
    }
}
