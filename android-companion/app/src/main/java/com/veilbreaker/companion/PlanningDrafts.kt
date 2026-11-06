package com.veilbreaker.companion

import android.content.Context
import org.json.JSONObject

/** Raw, operator-entered planning inputs. Blank fields are allowed for an unfinished draft. */
data class PlanningWifiDraft(val areaM2: String, val radiusM: String, val clients: String, val clientsPerAp: String)
data class PlanningFwaDraft(val antennaLatitude: String, val antennaLongitude: String, val siteLatitude: String, val siteLongitude: String, val frequencyMhz: String)

/** Versioned input-only records; a record is never a measurement or a capture. */
object PlanningDraftCodec {
    private const val FORMAT = "veilbreaker.android.planning_draft"
    private const val VERSION = 1
    private const val PROVENANCE = "operator_entered"
    private const val MAX_FIELD_LENGTH = 32
    private const val MAX_RECORD_LENGTH = 4096

    private fun validNumber(value: String, valid: (Double) -> Boolean): Boolean {
        if (value.length > MAX_FIELD_LENGTH) return false
        if (value.isBlank()) return true
        val number = value.trim().toDoubleOrNull() ?: return false
        return number.isFinite() && valid(number)
    }
    private fun validInteger(value: String, valid: (Int) -> Boolean): Boolean {
        if (value.length > MAX_FIELD_LENGTH) return false
        if (value.isBlank()) return true
        val number = value.trim().toIntOrNull() ?: return false
        return valid(number)
    }
    private fun validWifi(d: PlanningWifiDraft): Boolean {
        if (!validNumber(d.areaM2) { it > 0 } || !validNumber(d.radiusM) { it > 0 } ||
            !validInteger(d.clients) { it >= 0 } || !validInteger(d.clientsPerAp) { it > 0 }) return false
        if (listOf(d.areaM2, d.radiusM, d.clients, d.clientsPerAp).all { it.isNotBlank() }) {
            return PlanningModels.wifi(d.areaM2.trim().toDouble(), d.radiusM.trim().toDouble(),
                d.clients.trim().toInt(), d.clientsPerAp.trim().toInt()) != null
        }
        return true
    }
    private fun validFwa(d: PlanningFwaDraft): Boolean {
        if (!validNumber(d.antennaLatitude) { it in -90.0..90.0 } ||
            !validNumber(d.siteLatitude) { it in -90.0..90.0 } ||
            !validNumber(d.antennaLongitude) { it in -180.0..180.0 } ||
            !validNumber(d.siteLongitude) { it in -180.0..180.0 } ||
            !validNumber(d.frequencyMhz) { it > 0.0 && it <= 1e7 }) return false
        if (listOf(d.antennaLatitude, d.antennaLongitude, d.siteLatitude, d.siteLongitude, d.frequencyMhz).all { it.isNotBlank() }) {
            return PlanningModels.fwa(d.antennaLatitude.trim().toDouble(), d.antennaLongitude.trim().toDouble(),
                d.siteLatitude.trim().toDouble(), d.siteLongitude.trim().toDouble(), d.frequencyMhz.trim().toDouble()) != null
        }
        return true
    }
    private fun record(kind: String, inputs: JSONObject): String = JSONObject()
        .put("format", FORMAT).put("schema_version", VERSION).put("provenance", PROVENANCE)
        .put("kind", kind).put("inputs", inputs).toString()

    fun encodeWifi(draft: PlanningWifiDraft): String? = if (!validWifi(draft)) null else record("wifi", JSONObject()
        .put("area_m2", draft.areaM2).put("radius_m", draft.radiusM).put("clients", draft.clients).put("clients_per_ap", draft.clientsPerAp))
    fun encodeFwa(draft: PlanningFwaDraft): String? = if (!validFwa(draft)) null else record("fwa", JSONObject()
        .put("antenna_latitude", draft.antennaLatitude).put("antenna_longitude", draft.antennaLongitude)
        .put("site_latitude", draft.siteLatitude).put("site_longitude", draft.siteLongitude).put("frequency_mhz", draft.frequencyMhz))

    private fun inputs(encoded: String?, kind: String): JSONObject? {
        if (encoded == null || encoded.length > MAX_RECORD_LENGTH) return null
        return try {
            val record = JSONObject(encoded)
            if (record.opt("format") != FORMAT || record.opt("schema_version") != VERSION ||
                record.opt("provenance") != PROVENANCE || record.opt("kind") != kind) null
            else record.optJSONObject("inputs")
        } catch (_: Exception) { null }
    }
    private fun field(inputs: JSONObject, name: String): String? = inputs.opt(name) as? String

    fun decodeWifi(encoded: String?): PlanningWifiDraft? {
        val i = inputs(encoded, "wifi") ?: return null
        val draft = PlanningWifiDraft(field(i, "area_m2") ?: return null, field(i, "radius_m") ?: return null,
            field(i, "clients") ?: return null, field(i, "clients_per_ap") ?: return null)
        return draft.takeIf(::validWifi)
    }
    fun decodeFwa(encoded: String?): PlanningFwaDraft? {
        val i = inputs(encoded, "fwa") ?: return null
        val draft = PlanningFwaDraft(field(i, "antenna_latitude") ?: return null, field(i, "antenna_longitude") ?: return null,
            field(i, "site_latitude") ?: return null, field(i, "site_longitude") ?: return null, field(i, "frequency_mhz") ?: return null)
        return draft.takeIf(::validFwa)
    }
}

/** Call save only on an explicit operator action. Invalid input does not replace the saved draft. */
class PlanningDraftStore(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences("planning_drafts", Context.MODE_PRIVATE)
    private fun read(key: String): String? = try { preferences.getString(key, null) } catch (_: ClassCastException) { null }
    fun saveWifi(draft: PlanningWifiDraft): Boolean {
        val encoded = PlanningDraftCodec.encodeWifi(draft) ?: return false
        return preferences.edit().putString("wifi", encoded).commit()
    }
    fun saveFwa(draft: PlanningFwaDraft): Boolean {
        val encoded = PlanningDraftCodec.encodeFwa(draft) ?: return false
        return preferences.edit().putString("fwa", encoded).commit()
    }
    fun loadWifi(): PlanningWifiDraft? = PlanningDraftCodec.decodeWifi(read("wifi"))
    fun loadFwa(): PlanningFwaDraft? = PlanningDraftCodec.decodeFwa(read("fwa"))
    fun clearWifi(): Boolean = preferences.edit().remove("wifi").commit()
    fun clearFwa(): Boolean = preferences.edit().remove("fwa").commit()
}
