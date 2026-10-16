package com.veilbreaker.companion
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test
class UsbConnectionTest {
 @Test fun isolatesRepeatedCapturesAndExpiresApproval() {
  var clock=0L
  val conn=UsbConnection({clock},false,true,{}, {}, {}, {})
  conn.approve(true)
  fun start(id:String)=conn.command("start",conn.token,JSONObject().put("request_id",id).put("duration_s",5).put("cellular",false).put("location",true))
  val first=start("a").getString("session_id")
  assertThrows(IllegalArgumentException::class.java) { start("overlap") }
  conn.command("stop",conn.token,JSONObject().put("request_id","stop").put("session_id",first))
  val second=start("b").getString("session_id")
  assertNotEquals(first,second)
  assertThrows(IllegalArgumentException::class.java) { conn.command("sample",conn.token,JSONObject().put("request_id","stale").put("session_id",first)) }
  clock=3600000L
  assertThrows(IllegalArgumentException::class.java) { start("expired") }
 }
 @Test fun idleApprovalExpiresAndSingleUseCannotRestart() {
  var clock=0L
  val conn=UsbConnection({clock},true,false,{}, {}, {}, {})
  conn.approve(true);clock=900000
  assertThrows(IllegalArgumentException::class.java) { conn.command("start",conn.token,JSONObject().put("request_id","a").put("duration_s",5)) }
 }
}
