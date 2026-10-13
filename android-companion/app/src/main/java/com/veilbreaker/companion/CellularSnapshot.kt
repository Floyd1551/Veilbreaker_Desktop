package com.veilbreaker.companion

import android.os.Build
import android.telephony.*
import org.json.JSONArray
import org.json.JSONObject

object CellularSnapshot {
    @Suppress("DEPRECATION")
    fun cell(info: CellInfo, elapsed: Long): JSONObject {
        val timestamp = if (Build.VERSION.SDK_INT >= 30) info.timestampMillis else info.timeStamp / 1_000_000
        val identity = JSONObject()
        val signal = JSONObject()
        fun integer(name: String, value: Int) { identity.put(name, if (value == Int.MAX_VALUE || value < 0) JSONObject.NULL else value) }
        fun string(name: String, value: String?) { identity.put(name, value ?: JSONObject.NULL) }
        fun quantity(name: String, value: Int, unit: String, min: Int, max: Int) {
            signal.put(name, CaptureSerializer.quantity(value, unit, min, max))
        }
        val radio = when (info) {
            is CellInfoLte -> {
                val id = info.cellIdentity
                string("mcc", id.mccString); string("mnc", id.mncString)
                string("operator_alpha_long", id.operatorAlphaLong?.toString())
                string("cell_id", if (id.ci == Int.MAX_VALUE) null else id.ci.toString())
                integer("pci", id.pci); integer("tac", id.tac); integer("earfcn", id.earfcn)
                integer("bandwidth_khz", id.bandwidth)
                if (Build.VERSION.SDK_INT >= 30) identity.put("bands", JSONArray(id.bands.toList()))
                val ss = info.cellSignalStrength
                quantity("rsrp", ss.rsrp, "dBm", -160, -20)
                quantity("rsrq", ss.rsrq, "dB", -50, 20)
                quantity("rssi", ss.rssi, "dBm", -160, 0)
                quantity("rssnr", ss.rssnr, "dB", -30, 50)
                quantity("cqi", ss.cqi, "index", 0, 15)
                quantity("timing_advance", ss.timingAdvance, "index", 0, 1282)
                "LTE"
            }
            is CellInfoNr -> {
                val id = info.cellIdentity as CellIdentityNr
                string("mcc", id.mccString); string("mnc", id.mncString)
                string("operator_alpha_long", id.operatorAlphaLong?.toString())
                string("cell_id", if (id.nci == Long.MAX_VALUE) null else id.nci.toString())
                integer("pci", id.pci); integer("tac", id.tac); integer("nrarfcn", id.nrarfcn)
                if (Build.VERSION.SDK_INT >= 30) identity.put("bands", JSONArray(id.bands.toList()))
                val ss = info.cellSignalStrength as CellSignalStrengthNr
                quantity("ss_rsrp", ss.ssRsrp, "dBm", -160, -20)
                quantity("ss_rsrq", ss.ssRsrq, "dB", -50, 30)
                quantity("ss_sinr", ss.ssSinr, "dB", -30, 60)
                quantity("csi_rsrp", ss.csiRsrp, "dBm", -160, -20)
                quantity("csi_rsrq", ss.csiRsrq, "dB", -50, 30)
                quantity("csi_sinr", ss.csiSinr, "dB", -30, 60)
                "NR"
            }
            else -> info.javaClass.simpleName.removePrefix("CellInfo")
        }
        val role = when (info.cellConnectionStatus) {
            CellInfo.CONNECTION_PRIMARY_SERVING -> "primary"
            CellInfo.CONNECTION_SECONDARY_SERVING -> "secondary"
            CellInfo.CONNECTION_NONE -> "none"
            else -> "unknown"
        }
        return JSONObject().put("radio", radio).put("registered", info.isRegistered)
            .put("connection_status", role).put("age_ms", CaptureSerializer.age(elapsed, timestamp) ?: JSONObject.NULL)
            .put("identity", identity).put("signal", signal)
            .put("unsupported_radio", radio !in listOf("LTE", "NR"))
    }
}
