package com.veilbreaker.companion

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SurveyPendingWritesTest {
    @Test fun reopeningWaitsForRegisteredWriteButNotAnotherSurvey() {
        val writes = SurveyPendingWrites()
        val write = writes.register("survey-a")
        val waiting = CountDownLatch(1)
        val reopened = CountDownLatch(1)
        val worker = Thread {
            waiting.countDown()
            writes.await("survey-a")
            reopened.countDown()
        }
        try {
            worker.start()
            assertTrue(waiting.await(1, TimeUnit.SECONDS))
            assertFalse(reopened.await(100, TimeUnit.MILLISECONDS))
            val otherSurvey = CountDownLatch(1)
            Thread { writes.await("survey-b"); otherSurvey.countDown() }.start()
            assertTrue(otherSurvey.await(1, TimeUnit.SECONDS))
            write.close()
            assertTrue(reopened.await(1, TimeUnit.SECONDS))
        } finally {
            write.close()
            worker.join(1000)
        }
    }
}
