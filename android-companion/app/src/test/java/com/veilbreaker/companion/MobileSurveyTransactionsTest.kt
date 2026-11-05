package com.veilbreaker.companion

import org.junit.Assert.assertEquals
import org.junit.Assert.fail
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

class MobileSurveyTransactionsTest {
    @Test fun concurrentStoreClientsDoNotOverwriteEachOthersUpdates() {
        var value = 0
        val pool = Executors.newFixedThreadPool(4)
        val start = CountDownLatch(1)
        try {
            val futures = (1..4).map {
                pool.submit {
                    start.await()
                    repeat(200) {
                        MobileSurveyTransactions.update<Int>(
                            read = { value },
                            transform = { current -> Thread.yield(); current + 1 },
                            write = { value = it }
                        )
                    }
                }
            }
            start.countDown()
            futures.forEach { it.get(10, TimeUnit.SECONDS) }
            assertEquals(800, value)
        } finally { pool.shutdownNow() }
    }

    @Test fun rejectedMutationNeverWrites() {
        var value = 4
        try {
            MobileSurveyTransactions.update<Int>(read = { value }, transform = { throw IllegalArgumentException("rejected") }, write = { value = it })
            fail("Expected failed transform")
        } catch (_: IllegalArgumentException) { }
        assertEquals(4, value)
    }

    @Test fun updateCanCallOtherLockedStoreOperations() {
        var value = 2
        val result = MobileSurveyTransactions.update<Int>(
            read = { MobileSurveyTransactions.locked { value } },
            transform = { it + 1 },
            write = { MobileSurveyTransactions.locked { value = it } }
        )
        assertEquals(3, result)
        assertEquals(3, value)
    }
}
