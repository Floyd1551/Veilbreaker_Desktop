package com.veilbreaker.companion

import org.junit.Assert.*
import org.junit.Test
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

class OpenCellKeyVaultTest {
    private class MemoryStorage : OpenCellKeyStorage {
        var value: String? = null
        var fail = false
        override fun read(): String? { check(!fail); return value }
        override fun write(value: String): Boolean { check(!fail); this.value = value; return true }
        override fun clear(): Boolean { check(!fail); value = null; return true }
    }

    private fun key(): SecretKey = KeyGenerator.getInstance("AES").apply { init(256) }.generateKey()

    @Test fun roundTripStoresCiphertextAndUsesFreshNonces() {
        val storage = MemoryStorage()
        val encryptionKey = key()
        val vault = OpenCellKeyVaultEngine(storage) { encryptionKey }
        val sample = "example-not-a-credential"
        assertTrue(vault.save(sample))
        val first = storage.value!!
        assertFalse(first.contains(sample))
        assertEquals(sample, (vault.load() as OpenCellKeyReadResult.Available).key)
        assertTrue(vault.save(sample))
        assertNotEquals(first, storage.value)
        assertEquals(sample, (vault.load() as OpenCellKeyReadResult.Available).key)
    }

    @Test fun corruptionAndWrongKeyAreUnavailable() {
        val storage = MemoryStorage()
        val encryptionKey = key()
        val vault = OpenCellKeyVaultEngine(storage) { encryptionKey }
        assertTrue(vault.save("example-not-a-credential"))
        val wrongKey = key()
        assertTrue(OpenCellKeyVaultEngine(storage) { wrongKey }.load() is OpenCellKeyReadResult.Unavailable)
        storage.value = "not-an-envelope"
        assertTrue(vault.load() is OpenCellKeyReadResult.Unavailable)
    }

    @Test fun emptyBlankClearAndStorageFailuresAreSafe() {
        val storage = MemoryStorage()
        val vault = OpenCellKeyVaultEngine(storage) { key() }
        assertTrue(vault.load() is OpenCellKeyReadResult.Empty)
        assertFalse(vault.save("  "))
        assertNull(storage.value)
        assertTrue(vault.save("example-not-a-credential"))
        assertTrue(vault.clear())
        assertTrue(vault.load() is OpenCellKeyReadResult.Empty)
        storage.fail = true
        assertTrue(vault.load() is OpenCellKeyReadResult.Unavailable)
        assertFalse(vault.save("example-not-a-credential"))
        assertFalse(vault.clear())
    }

    @Test fun keyProviderFailureDoesNotOverwriteStoredValue() {
        val storage = MemoryStorage()
        storage.value = "prior-value"
        val vault = OpenCellKeyVaultEngine(storage) { throw IllegalStateException() }
        assertFalse(vault.save("example-not-a-credential"))
        assertEquals("prior-value", storage.value)
        assertTrue(vault.load() is OpenCellKeyReadResult.Unavailable)
    }
}
