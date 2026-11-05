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
        val details = JSONObject()
        fun integer(name: String, value: Int) { CellularExtras.identityInteger(identity, name, value) }
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
                if (Build.VERSION.SDK_INT >= 31) {
                    try { quantity("lte_cqi_table_index", ss.cqiTableIndex, "index", 1, 6) } catch (_: RuntimeException) { /* Optional OEM field unavailable. */ }
                }
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
                if (Build.VERSION.SDK_INT >= 31) {
                    try { quantity("nr_csi_cqi_table_index", ss.csiCqiTableIndex, "index", 1, 3) } catch (_: RuntimeException) { /* Optional OEM field unavailable. */ }
                    try { ss.csiCqiReport?.let { CellularExtras.nrCqiReport(details, it) } } catch (_: RuntimeException) { /* Retain other measurements. */ }
                }
                "NR"
            }
            is CellInfoGsm -> {
                val id = info.cellIdentity
                string("mcc", id.mccString); string("mnc", id.mncString)
                string("operator_alpha_long", id.operatorAlphaLong?.toString())
                CellularExtras.cellId(identity, id.cid)
                integer("lac", id.lac); integer("arfcn", id.arfcn); integer("bsic", id.bsic)
                val ss = info.cellSignalStrength
                quantity("rssi", ss.dbm, "dBm", -160, 0)
                quantity("gsm_bit_error_rate_index", ss.bitErrorRate, "index", 0, 7)
                quantity("timing_advance", ss.timingAdvance, "index", 0, 219)
                "GSM"
            }
            is CellInfoWcdma -> {
                val id = info.cellIdentity
                string("mcc", id.mccString); string("mnc", id.mncString)
                string("operator_alpha_long", id.operatorAlphaLong?.toString())
                CellularExtras.cellId(identity, id.cid)
                integer("lac", id.lac); integer("uarfcn", id.uarfcn); integer("psc", id.psc)
                val ss = info.cellSignalStrength
                quantity("rscp", ss.dbm, "dBm", -120, -24)
                if (Build.VERSION.SDK_INT >= 30) quantity("ecno", ss.ecNo, "dB", -24, 1)
                "WCDMA"
            }
            is CellInfoTdscdma -> {
                val id = info.cellIdentity
                string("mcc", id.mccString); string("mnc", id.mncString)
                string("operator_alpha_long", id.operatorAlphaLong?.toString())
                CellularExtras.cellId(identity, id.cid)
                integer("lac", id.lac); integer("uarfcn", id.uarfcn); integer("cpid", id.cpid)
                quantity("rscp", info.cellSignalStrength.dbm, "dBm", -120, -24)
                "TDSCDMA"
            }
            is CellInfoCdma -> {
                val id = info.cellIdentity
                string("operator_alpha_long", id.operatorAlphaLong?.toString())
                integer("system_id", id.systemId); integer("network_id", id.networkId); integer("base_station_id", id.basestationId)
                val ss = info.cellSignalStrength
                quantity("cdma_rssi", ss.cdmaDbm, "dBm", -160, 0)
                quantity("cdma_ecio_tenths_db", ss.cdmaEcio, "0.1 dB", -500, 0)
                quantity("evdo_rssi", ss.evdoDbm, "dBm", -160, 0)
                quantity("evdo_ecio_tenths_db", ss.evdoEcio, "0.1 dB", -500, 0)
                quantity("evdo_snr_index", ss.evdoSnr, "index", 0, 8)
                "CDMA"
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
            .apply { if (details.length() > 0) put("radio_details", details) }
    }
}
