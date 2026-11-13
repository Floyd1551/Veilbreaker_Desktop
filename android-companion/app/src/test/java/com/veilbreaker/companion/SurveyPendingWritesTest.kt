package com.veilbreaker.companion

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Assert.assertEquals
import org.junit.Test

class SurveyPendingWritesTest {
    @Test fun listingWaitsForAllPendingMutationsIncludingCreationAndDeletion() {
        val writes = SurveyPendingWrites()
        val first = writes.register("create")
        val second = writes.register("delete")
        val reopened = CountDownLatch(1)
        val worker = Thread { writes.awaitAll(); reopened.countDown() }
        try {
            worker.start()
            assertFalse(reopened.await(100, TimeUnit.MILLISECONDS))
            first.close()
            assertFalse(reopened.await(100, TimeUnit.MILLISECONDS))
            second.close()
            assertTrue(reopened.await(1, TimeUnit.SECONDS))
        } finally {
            first.close(); second.close(); worker.join(1000)
        }
    }

    @Test fun reopeningObservesCompletedMutation() {
        val writes = SurveyPendingWrites()
        val write = writes.register("survey")
        var stored = "open"
        val reopened = CountDownLatch(1)
        var observed = ""
        val worker = Thread { writes.await("survey"); observed = stored; reopened.countDown() }
        try {
            worker.start()
            assertFalse(reopened.await(100, TimeUnit.MILLISECONDS))
            stored = "completed"
            write.close()
            assertTrue(reopened.await(1, TimeUnit.SECONDS))
            assertEquals("completed", observed)
        } finally {
            write.close(); worker.join(1000)
        }
    }
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
