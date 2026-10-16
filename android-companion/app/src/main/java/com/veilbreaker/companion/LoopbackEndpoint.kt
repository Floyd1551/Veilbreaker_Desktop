package com.veilbreaker.companion

import org.json.JSONObject
import java.net.InetAddress
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.atomic.AtomicBoolean

/** Deliberately small HTTP endpoint, bound exclusively to IPv4 loopback. */
class LoopbackEndpoint(private val command: (String, String, JSONObject) -> JSONObject) : AutoCloseable {
    private val open = AtomicBoolean(true)
    private val server = ServerSocket(8765, 4, InetAddress.getByName("127.0.0.1"))
    private val thread = Thread {
        while (open.get()) {
            try { server.accept().use { serve(it) } } catch (_: Exception) { }
        }
    }.apply { isDaemon = true; name = "Veilbreaker USB"; start() }

    private fun serve(socket: Socket) {
        socket.soTimeout = 2000
        var status = 200
        val body = try {
            val input = socket.getInputStream()
            var headerBytes = 0
            fun line(): String {
                val data = StringBuilder()
                while (true) {
                    val b = input.read()
                    require(b >= 0 && ++headerBytes <= 8192)
                    if (b == 10) return data.toString().trimEnd('\r')
                    data.append(b.toChar())
                }
            }
            val first = line().split(' ')
            require(first.size == 3 && first[0] == "POST" && first[1] in listOf("/start", "/sample", "/status", "/stop", "/pair", "/pair_status", "/disconnect"))
            val headers = mutableMapOf<String, String>()
            while (true) {
                val item = line(); if (item.isEmpty()) break
                val pair = item.split(':', limit = 2); require(pair.size == 2)
                val name = pair[0].lowercase(); require(!headers.containsKey(name)); headers[name] = pair[1].trim()
            }
            require(!headers.containsKey("transfer-encoding"))
            val length = headers["content-length"]?.toIntOrNull() ?: 0
            require(length in 1..4096)
            val data = ByteArray(length)
            var offset = 0
            while (offset < length) { val n = input.read(data, offset, length - offset); require(n > 0); offset += n }
            val token = headers["authorization"]?.removePrefix("Bearer ") ?: ""
            command(first[1].removePrefix("/"), token, JSONObject(String(data, Charsets.UTF_8))).toString()
        } catch (_: Exception) { status = 400; "{\"error\":\"Request rejected\"}" }
        val data = body.toByteArray(Charsets.UTF_8)
        require(data.size <= 16 * 1024 * 1024)
        val output = socket.getOutputStream()
        output.write("HTTP/1.1 $status Result\r\nContent-Type: application/json\r\nContent-Length: ${data.size}\r\nConnection: close\r\n\r\n".toByteArray())
        output.write(data); output.flush()
    }
    override fun close() { open.set(false); server.close() }
}
