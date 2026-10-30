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
 @Test fun optionalFieldsCannotAddCoordinatesToAnUnavailableFix() {
  val unavailable=LocationEvidence.fix(40.0,-90.0,null,100000L,100L,200L,"gps",false)
  LocationEvidence.addOptional(unavailable,120.0,5.0,1.0,25.0)
  assertEquals("unavailable",unavailable.getString("status"))
  assertFalse(unavailable.has("altitude_m"))
  assertFalse(unavailable.has("speed_mps"))
 }
 @Test fun optionalFieldsAreFiniteAndInsideDesktopSchemaBounds() {
  val fix=LocationEvidence.fix(40.0,-90.0,5.0,100000L,100L,200L,"gps",false)
  LocationEvidence.addOptional(fix,Double.NaN,-1.0,Double.POSITIVE_INFINITY,360.0)
  for(key in listOf("altitude_m","altitude_reference","vertical_accuracy_m","speed_mps","bearing_deg")) assertFalse(fix.has(key))
  LocationEvidence.addOptional(fix,120.5,6.0,2.0,359.5)
  assertEquals(120.5,fix.getDouble("altitude_m"),0.001)
  assertEquals("ellipsoid",fix.getString("altitude_reference"))
  assertEquals(6.0,fix.getDouble("vertical_accuracy_m"),0.001)
  assertEquals(2.0,fix.getDouble("speed_mps"),0.001)
  assertEquals(359.5,fix.getDouble("bearing_deg"),0.001)
 }
 @Test fun invalidHorizontalAccuracyIsUnavailable() {
  assertEquals("unavailable",LocationEvidence.fix(40.0,-90.0,1000000001.0,100000,100,200,"gps",false).getString("status"))
  assertEquals("gnss",LocationEvidence.fix(40.0,-90.0,5.0,100000,100,200," ",false).getString("provider"))
 }
 @Test fun capturedLocationStatusLabelsAgeAtReceiptAndNotAsLiveFix() {
  val fix=LocationEvidence.fix(40.0,-90.0,5.0,100000L,100L,200L,"gps",false)
  val original=fix.toString()
  assertEquals("Captured fix · ±5 m · 0s old at receipt",LocationEvidence.describeCaptured(fix))
  assertEquals(original,fix.toString())
  assertTrue(LocationEvidence.describeCaptured(LocationEvidence.unavailable("disabled")).contains("at capture"))
  val old=LocationEvidence.fix(40.0,-90.0,5.0,100000L,100L,20100L,"gps",false)
  assertTrue(LocationEvidence.describeCaptured(old).contains("Old fix at capture"))
  fix.put("fix_age_ms",org.json.JSONObject.NULL)
  assertTrue(LocationEvidence.describeCaptured(fix).contains("age unavailable at receipt"))
 }
}
