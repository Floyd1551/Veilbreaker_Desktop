package com.veilbreaker.companion

import org.json.JSONObject
import java.util.UUID

/** A filename/display identity derived from the actual serialized capture snapshot. */
object CaptureExportIdentity {
    fun validated(value: String?): String? {
        if (value == null || value.length != 36) return null
        return try { UUID.fromString(value).toString().takeIf { it == value } } catch (_: Exception) { null }
    }

    fun fromSnapshot(snapshot: String): String? = try {
        validated(JSONObject(snapshot).optString("capture_id", ""))
    } catch (_: Exception) { null }
}
