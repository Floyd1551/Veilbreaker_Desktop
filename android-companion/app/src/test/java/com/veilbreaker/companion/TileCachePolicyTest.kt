package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test

class TileCachePolicyTest {
    @Test fun maxAgeUsesServerPolicy() {
        assertEquals(121000L, TileCachePolicy.expiry(1000L, "public, max-age=120", null, null))
    }
    @Test fun absentCachingHeadersUsesSevenDayFallback() {
        assertEquals(1000L + 7L * 24 * 60 * 60 * 1000, TileCachePolicy.expiry(1000L, null, null, null))
    }
    @Test fun noStoreIsNotCachedAndNoCacheRequiresRevalidation() {
        assertNull(TileCachePolicy.expiry(1000L, "no-store", null, null))
        assertEquals(1000L, TileCachePolicy.expiry(1000L, "no-cache, max-age=600", null, null))
    }
    @Test fun malformedMaxAgeDoesNotOverflowOrCacheForever() {
        assertEquals(1000L + 7L * 24 * 60 * 60 * 1000, TileCachePolicy.expiry(1000L, "max-age=999999999999999999999", null, null))
    }
    @Test fun invalidTilesCannotBeRequested() {
        assertFalse(TileKey(-1, 0, 0).valid())
        assertFalse(TileKey(2, 4, 0).valid())
        assertFalse(TileKey(2, 0, -1).valid())
        assertTrue(TileKey(2, 3, 3).valid())
    }
}
