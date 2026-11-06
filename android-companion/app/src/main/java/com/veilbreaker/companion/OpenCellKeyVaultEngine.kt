package com.veilbreaker.companion

import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

sealed class OpenCellKeyReadResult {
    object Empty : OpenCellKeyReadResult()
    class Available(val key: String) : OpenCellKeyReadResult()
    object Unavailable : OpenCellKeyReadResult()
}

internal interface OpenCellKeyStorage {
    fun read(): String?
    fun write(value: String): Boolean
    fun clear(): Boolean
}

/** Storage-independent vault logic. The key provider creates a key only for writes. */
internal class OpenCellKeyVaultEngine(
    private val storage: OpenCellKeyStorage,
    private val keyProvider: (create: Boolean) -> SecretKey?,
) {
    fun load(): OpenCellKeyReadResult {
        return try {
            val encoded = storage.read() ?: return OpenCellKeyReadResult.Empty
            val key = keyProvider(false) ?: return OpenCellKeyReadResult.Unavailable
            val plaintext = OpenCellKeyCipher.decrypt(key, encoded)
            if (plaintext.isBlank()) OpenCellKeyReadResult.Unavailable else OpenCellKeyReadResult.Available(plaintext)
        } catch (_: Exception) {
            OpenCellKeyReadResult.Unavailable
        }
    }

    fun save(value: String): Boolean {
        if (value.isBlank()) return false
        return try {
            val key = keyProvider(true) ?: return false
            storage.write(OpenCellKeyCipher.encrypt(key, value))
        } catch (_: Exception) {
            false
        }
    }

    fun clear(): Boolean = try { storage.clear() } catch (_: Exception) { false }
}

internal object OpenCellKeyCipher {
    private const val PREFIX = "v1:"
    private const val NONCE_SIZE = 12
    private const val TAG_SIZE_BITS = 128
    private const val MAX_ENCODED_SIZE = 65536

    fun encrypt(key: SecretKey, plaintext: String): String {
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key)
        val nonce = cipher.iv
        require(nonce.size == NONCE_SIZE)
        val ciphertext = cipher.doFinal(plaintext.toByteArray(Charsets.UTF_8))
        val encoded = PREFIX + Base64.getEncoder().encodeToString(nonce + ciphertext)
        require(encoded.length <= MAX_ENCODED_SIZE)
        return encoded
    }

    fun decrypt(key: SecretKey, encoded: String): String {
        require(encoded.startsWith(PREFIX) && encoded.length <= MAX_ENCODED_SIZE)
        val bytes = Base64.getDecoder().decode(encoded.substring(PREFIX.length))
        require(bytes.size >= NONCE_SIZE + TAG_SIZE_BITS / 8)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key, GCMParameterSpec(TAG_SIZE_BITS, bytes, 0, NONCE_SIZE))
        return cipher.doFinal(bytes, NONCE_SIZE, bytes.size - NONCE_SIZE).toString(Charsets.UTF_8)
    }
}
