package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class OpenCellLookupTest {
    @Test fun validatesIdentifiersAndAllowsNrCellIds() {
        assertNotNull(OpenCellLookup.query("310", "260", "65535", "68719476735", "NR"))
        assertNull(OpenCellLookup.query("31", "260", "1", "2", "LTE"))
        assertNull(OpenCellLookup.query("310", "260", "-1", "2", "LTE"))
        assertNull(OpenCellLookup.query("310", "260", "1", "68719476736", "NR"))
        assertNull(OpenCellLookup.query("310", "260", "1", "2", "other"))
    }

    @Test fun rejectsErrorsMismatchedCellsAndInvalidPositions() {
        val q = OpenCellLookup.query("310", "260", "123", "456", "LTE")!!
        assertNull(OpenCellLookup.parse("{\"error\":\"secret\",\"code\":2}", q))
        assertNull(OpenCellLookup.parse("{\"lat\":91,\"lon\":0,\"mcc\":310,\"mnc\":260,\"lac\":123,\"cellid\":456,\"radio\":\"LTE\"}", q))
        assertNull(OpenCellLookup.parse("{\"lat\":34,\"lon\":-86,\"mcc\":310,\"mnc\":260,\"lac\":123,\"cellid\":457,\"radio\":\"LTE\"}", q))
    }

    @Test fun parsesAnExactCandidate() {
        val q = OpenCellLookup.query("310", "260", "123", "456", "LTE")!!
        val result = OpenCellLookup.parse("{\"lat\":34.7,\"lon\":-86.6,\"mcc\":310,\"mnc\":260,\"lac\":123,\"cellid\":456,\"radio\":\"LTE\",\"samples\":5,\"range\":900}", q)!!
        assertEquals(34.7, result.latitude, 0.00001)
        assertEquals(5L, result.samples)
        assertEquals(900L, result.rangeMeters)
    }

    @Test fun locatedCandidateRetainsQueryAndRetrievalTimeOnlyForExactResponse() {
        val q = OpenCellLookup.query("310", "260", "123", "456", "LTE")!!
        val time = java.time.Instant.parse("2026-01-02T03:04:05Z")
        val body = "{\"lat\":34.7,\"lon\":-86.6,\"mcc\":310,\"mnc\":260,\"lac\":123,\"cellid\":456,\"radio\":\"LTE\",\"samples\":5,\"range\":900}"
        val located = OpenCellLookup.locate(body, q, time)!!
        assertEquals(q, located.query)
        assertEquals(time, located.retrievedAt)
        assertEquals(34.7, located.candidate.latitude, 0.00001)
        assertNull(OpenCellLookup.locate(body.replace("456", "457"), q, time))
        assertNull(OpenCellLookup.locate(body.replace("\"cellid\":456", "\"cellid\":456.5"), q, time))
    }
}
