package com.veilbreaker.companion

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/** Optional, app-private credential storage. No credential is persisted unless save is called. */
class OpenCellApiKeyVault(context: Context) {
    private val preferences = context.applicationContext.getSharedPreferences(PREFERENCES, Context.MODE_PRIVATE)
    private val engine = OpenCellKeyVaultEngine(object : OpenCellKeyStorage {
        override fun read(): String? = preferences.getString(VALUE, null)
        override fun write(value: String): Boolean = preferences.edit().putString(VALUE, value).commit()
        override fun clear(): Boolean = preferences.edit().remove(VALUE).commit()
    }, ::getKey)

    @Synchronized fun load(): OpenCellKeyReadResult = engine.load()
    @Synchronized fun save(key: String): Boolean = engine.save(key)

    /** Removes the ciphertext and its encryption key. A failure is reported without exposing details. */
    @Synchronized fun clear(): Boolean {
        if (!engine.clear()) return false
        return try {
            keyStore().deleteEntry(KEY_ALIAS)
            true
        } catch (_: Exception) {
            false
        }
    }

    private fun keyStore(): KeyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

    private fun getKey(create: Boolean): SecretKey? {
        val store = keyStore()
        val existing = store.getKey(KEY_ALIAS, null)
        if (existing != null) return existing as? SecretKey
        if (!create) return null
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").run {
            init(KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build())
            generateKey()
        }
    }

    private companion object {
        const val PREFERENCES = "opencellid_key_vault"
        const val VALUE = "encrypted_key"
        const val KEY_ALIAS = "opencellid_api_key_v1"
    }
}
