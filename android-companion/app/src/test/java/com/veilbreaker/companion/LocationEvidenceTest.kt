package com.veilbreaker.companion
import org.junit.Assert.*
import org.junit.Test
class LocationEvidenceTest {
 @Test fun preservesAgeAccuracyAndRejectsFutureFix() {
  val fix=LocationEvidence.fix(40.0,-90.0,5.0,100000L,100L,200L,"gps",false)
  assertEquals(100L,fix.getLong("fix_age_ms"))
  assertEquals("unavailable",LocationEvidence.fix(40.0,-90.0,null,100000,100,200,"gps",false).getString("status"))
  assertEquals("unavailable",LocationEvidence.fix(40.0,-90.0,5.0,100000,300,200,"gps",false).getString("status"))
 }
}
