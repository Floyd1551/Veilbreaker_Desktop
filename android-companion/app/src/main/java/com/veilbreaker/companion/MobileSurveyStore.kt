package com.veilbreaker.companion

import android.content.Context
import android.util.AtomicFile
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File

/** Private on-device journal. Captures are copied, never changed in place. */
class MobileSurveyStore(context: Context, archive: Boolean = false) {
    data class Summary(val id: String, val name: String, val state: String, val created: String, val count: Int)
    data class Listing(val surveys: List<Summary>, val unavailable: Int)
    private val directory = File(context.filesDir, if (archive) "capture-archive" else "mobile-surveys")
    private val idPattern = Regex("[a-f0-9-]{36}")
    private val totalLimit = 64L * 1024 * 1024

    private fun file(id: String): File {
        require(idPattern.matches(id)) { "Invalid survey ID." }
        return File(directory, "$id.json")
    }
    fun exists(id: String): Boolean = MobileSurveyTransactions.locked {
        val target = file(id)
        target.exists() || File(target.path + ".bak").exists()
    }

    fun load(id: String): JSONObject = MobileSurveyTransactions.locked {
        val target = file(id)
        if (!target.exists() && !File(target.path + ".bak").exists()) throw IllegalArgumentException("Survey is unavailable.")
        val bytes = AtomicFile(target).openRead().use { input ->
            val output = ByteArrayOutputStream(); val buffer = ByteArray(65536); var count = 0
            while (true) {
                val read = input.read(buffer); if (read < 0) break
                count += read; require(count <= MobileSurvey.MAX_BYTES) { "Survey exceeds the size limit." }
                output.write(buffer, 0, read)
            }
            output.toByteArray()
        }
        val survey = try { JSONObject(String(bytes, Charsets.UTF_8)) } catch (_: Exception) { throw IllegalArgumentException("Survey data is invalid.") }
        require(survey.optString("survey_id") == id) { "Survey identity mismatch." }
        MobileSurvey.validate(survey)
    }

    fun save(survey: JSONObject) = MobileSurveyTransactions.locked {
        MobileSurvey.validate(survey)
        val id = survey.getString("survey_id"); val target = file(id)
        require(directory.isDirectory || directory.mkdirs()) { "Cannot create mobile survey storage." }
        val all = directory.listFiles()?.filter { it.isFile && it.name.endsWith(".json") } ?: emptyList()
        require(target.exists() || all.size < 100) { "Mobile survey limit reached." }
        val data = survey.toString().toByteArray(Charsets.UTF_8)
        require(all.sumOf { if (it.name == target.name) 0L else it.length() } + data.size <= totalLimit) { "Mobile survey storage limit reached (64 MiB)." }
        val atomic = AtomicFile(target); val output = atomic.startWrite()
        try { output.write(data); atomic.finishWrite(output) } catch (e: Exception) { atomic.failWrite(output); throw e }
    }

    /** Reload and mutate the current on-disk record without racing another store instance. */
    fun update(id: String, transform: (JSONObject) -> JSONObject): JSONObject = MobileSurveyTransactions.update(
        read = { load(id) },
        transform = { current ->
            val updated = transform(current)
            require(updated.optString("survey_id") == id) { "Survey identity mismatch." }
            updated
        },
        write = { updated -> save(updated) }
    )

    fun delete(id: String) = MobileSurveyTransactions.locked {
        MobileSurveyFiles.delete(directory, id)
    }

    fun list(): Listing = MobileSurveyTransactions.locked {
        if (!directory.exists()) return@locked Listing(emptyList(), 0)
        val files = directory.listFiles()?.filter {
            val base = it.name.removeSuffix(".bak")
            base.endsWith(".json") && idPattern.matches(base.removeSuffix(".json"))
        }
            ?: throw IllegalArgumentException("Cannot read mobile survey storage.")
        val ids = files.map { it.name.removeSuffix(".bak").removeSuffix(".json") }.distinct()
        require(ids.size <= 100 && files.sumOf { it.length() } <= totalLimit) { "Mobile survey storage exceeds its bounds." }
        val summaries = mutableListOf<Summary>(); var unavailable = 0
        for (id in ids) {
            try {
                val row = load(id)
                summaries.add(Summary(row.getString("survey_id"), row.getString("name"), row.getString("lifecycle"),
                    row.getString("created_utc"), row.getJSONArray("points").length()))
            } catch (_: Exception) { unavailable++ }
        }
        Listing(summaries.sortedByDescending { it.created }, unavailable)
    }
}
