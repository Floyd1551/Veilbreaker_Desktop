package com.veilbreaker.companion
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class UsbSessionTest {
    @Test fun rejectsWrongTokenAndUnstartedSample() {
        val session = UsbSession({ 0L }, {}, {})
        assertThrows(IllegalArgumentException::class.java) { session.command("status", "wrong", JSONObject().put("request_id", "r")) }
        assertThrows(IllegalArgumentException::class.java) { session.command("sample", session.token, JSONObject().put("request_id", "r").put("session_id", session.id)) }
    }
    @Test fun boundsCadenceAndIgnoresLateCallbacks() {
        var clock = 0L
        var requests = 0
        val session = UsbSession({clock}, {requests++}, {})
        fun cmd(name: String, id: String) = session.command(name, session.token, JSONObject().put("request_id", id).put("session_id", session.id).put("duration_s", 10))
        cmd("start", "1"); cmd("sample", "2"); assertEquals(1, requests)
        cmd("sample", "3"); assertEquals(1, requests)
        session.finish("cancelled")
        val snapshot = CaptureSerializer.envelope("test", "test", "13", 33, "test", emptyList(), 1, "partial", emptyList())
        session.accept(snapshot)
        assertFalse(cmd("status", "4").has("capture"))
        assertEquals("cancelled", cmd("status", "5").getString("status"))
    }
    @Test fun rejectsInvalidDurationAndDuplicateRequest() {
        val session = UsbSession({0L}, {}, {})
        val body = JSONObject().put("request_id", "1").put("duration_s", 301)
        assertThrows(IllegalArgumentException::class.java) { session.command("start", session.token, body) }
        body.put("request_id", "2").put("duration_s", 5)
        session.command("start", session.token, body)
        assertThrows(IllegalArgumentException::class.java) { session.command("start", session.token, body) }
    }
    @Test fun sessionExportHasNoTokenAndDeadlineStopsSampling() {
        var clock = 0L
        var saved: JSONObject? = null
        val session = UsbSession({clock}, {}, {saved=it})
        fun cmd(name: String, id: String) = session.command(name, session.token, JSONObject().put("request_id", id).put("session_id", session.id).put("duration_s", 5))
        cmd("start", "1"); cmd("sample", "2")
        session.accept(CaptureSerializer.envelope("test", "test", "13", 33, "test", emptyList(), 1, "partial", emptyList()))
        clock = 5000; session.expire()
        assertEquals("partial", cmd("status", "3").getString("status"))
        assertEquals("session", saved!!.getJSONObject("collection").getString("mode"))
        assertFalse(saved.toString().contains(session.token))
        val file = java.io.File("build/session-fixture.json")
        file.parentFile.mkdirs(); file.writeText(saved.toString())
    }
}
