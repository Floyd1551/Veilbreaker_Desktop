package com.veilbreaker.companion

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class GpsSpatialModelTest {
    @Test fun extentRejectsInvalidBoundsAndMapsNorthUp() {
        assertNull(GpsSpatialModel.bounds(-87.0, 35.0, -88.0, 36.0))
        assertNull(GpsSpatialModel.bounds(-180.0, -90.0, 180.0, 90.0))
        assertNull(GpsSpatialModel.bounds(Double.NaN, 34.0, -86.0, 35.0))
        val bounds = GpsSpatialModel.bounds(-87.0, 34.0, -86.0, 35.0)!!
        assertEquals(Pair(0.0, 0.0), GpsSpatialModel.mapPoint(bounds, 35.0, -87.0))
        assertEquals(Pair(1.0, 1.0), GpsSpatialModel.mapPoint(bounds, 34.0, -86.0))
        assertNull(GpsSpatialModel.mapPoint(bounds, 36.0, -87.0))
    }

    @Test fun observationsKeepAvailableLocationsAndReceiptProvenance() {
        fun loc(lat: Any, lon: Any, status: String = "available") = JSONObject()
            .put("status", status).put("latitude_deg", lat).put("longitude_deg", lon)
            .put("horizontal_accuracy_m", 8).put("fix_age_ms", 1200).put("provider", "gps").put("mock", true)
        val observations = JSONArray()
            .put(JSONObject().put("received_utc", "2026-10-01T00:00:00Z").put("location", loc(34.7, -86.6)))
            .put(JSONObject().put("location", loc(0, 0, "unavailable")))
            .put(JSONObject().put("location", loc(999, 0)))
        val result = GpsSpatialModel.savedFixes(JSONObject().put("observations", observations))
        assertEquals(1, result.size)
        assertEquals(34.7, result[0].latitude, 0.00001)
        assertEquals(8.0, result[0].accuracy, 0.00001)
        assertEquals(1200L, result[0].ageAtReceiptMs)
        assertEquals(true, result[0].mock)
        assertEquals("2026-10-01T00:00:00Z", result[0].receivedUtc)
    }

    @Test fun mockStatusPreservesUnknownInsteadOfAssumingFalse() {
        val location = JSONObject().put("status", "available").put("latitude_deg", 30.0)
            .put("longitude_deg", -80.0).put("horizontal_accuracy_m", 5.0)
        assertNull(GpsSpatialModel.fix(location)!!.mock)
        assertEquals("mock status unknown", GpsSpatialModel.fix(location)!!.mockLabel())
        location.put("mock", JSONObject.NULL)
        assertNull(GpsSpatialModel.fix(location)!!.mock)
        location.put("mock", "false")
        assertNull(GpsSpatialModel.fix(location)!!.mock)
        location.put("mock", false)
        assertEquals(false, GpsSpatialModel.fix(location)!!.mock)
        assertEquals("not marked mock", GpsSpatialModel.fix(location)!!.mockLabel())
        location.put("mock", true)
        assertEquals(true, GpsSpatialModel.fix(location)!!.mock)
        assertEquals("mock location", GpsSpatialModel.fix(location)!!.mockLabel())
    }

    @Test fun unavailableOrMalformedAccuracyIsNeverInvented() {
        assertNull(GpsSpatialModel.fix(JSONObject().put("status", "available").put("latitude_deg", 30.0).put("longitude_deg", -80.0)))
        assertNull(GpsSpatialModel.fix(JSONObject().put("status", "available").put("latitude_deg", 30.0).put("longitude_deg", -80.0).put("horizontal_accuracy_m", -5)))
        assertNull(GpsSpatialModel.fix(JSONObject().put("status", "unavailable")))
    }

    @Test fun imageDecodingIsBoundedBeforeAllocation() {
        assertEquals(1, GpsSpatialModel.imageSampleSize(1200, 800))
        assertEquals(4, GpsSpatialModel.imageSampleSize(8000, 6000))
        assertNull(GpsSpatialModel.imageSampleSize(12001, 1))
        assertNull(GpsSpatialModel.imageSampleSize(10000, 10000))
        assertNull(GpsSpatialModel.imageSampleSize(0, 10))
    }

    @Test fun rotatedOrMalformedExifIsRejectedBeforeMapOverlay() {
        assertTrue(GpsSpatialModel.isMapOrientationSafe(null))
        assertTrue(GpsSpatialModel.isMapOrientationSafe("1"))
        for (orientation in listOf("0", "2", "3", "4", "5", "6", "7", "8", "invalid"))
            assertFalse(GpsSpatialModel.isMapOrientationSafe(orientation))
    }
}
