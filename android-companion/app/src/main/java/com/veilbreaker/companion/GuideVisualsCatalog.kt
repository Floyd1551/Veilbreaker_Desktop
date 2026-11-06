package com.veilbreaker.companion

/** Offline editorial diagrams. These are field guidance, not device evidence. */
object GuideVisualsCatalog {
    data class Stage(val title: String, val detail: String)
    data class Cue(val observation: String, val nextStep: String)
    data class Guide(val stages: List<Stage>, val cues: List<Cue>)

    private fun guide(a: Pair<String, String>, b: Pair<String, String>, c: Pair<String, String>, d: Pair<String, String>,
                      first: Pair<String, String>, second: Pair<String, String>) = Guide(
        listOf(a, b, c, d).map { Stage(it.first, it.second) },
        listOf(first, second).map { Cue(it.first, it.second) })

    val entries = mapOf(
        "expanded-guide-wifi" to guide(
            "PLAN" to "Define clients, floors and acceptance criteria.", "MEASURE" to "Collect repeatable locations and connection details.",
            "INVESTIGATE" to "Compare signal, roaming and a known service test.", "REPORT" to "Retest changes and preserve gaps and conditions.",
            "Weak signal" to "Repeat nearby and inspect location and AP placement.", "Strong signal, slow service" to "Check quality, contention, AP uplink and test target."),
        "expanded-guide-fwa" to guide(
            "BASELINE" to "Record modem, carrier, bands and indoor performance.", "COMPARE" to "Test candidate positions and orientations consistently.",
            "TUNE" to "Adjust one variable at a time and let readings settle.", "VERIFY" to "Retest the installation and preserve before/after data.",
            "Power improves, quality falls" to "Compare band, cell and interference indicators.", "Crowdsourced candidate" to "Treat as a lead; verify the actual serving path."),
        "expanded-guide-das" to guide(
            "SCOPE" to "Define floors, carriers, test device and pass criteria.", "PLACE" to "Keep floor-plan placement and GPS provenance distinct.",
            "CAPTURE" to "Record available signal, quality and repeatable tests.", "ASSESS" to "Repeat anomalies and report missing or unplaced data.",
            "Same cell ID at two points" to "Do not assume they share a physical DAS remote.", "No usable GPS" to "Use operator placement or retain an unplaced point."),
        "expanded-guide-rf" to guide(
            "DEFINE" to "Record path, antennas, frequency and link requirements.", "PROFILE" to "Inspect verified terrain and obstacle data.",
            "CALCULATE" to "Budget gains, losses and receiver margin both ways.", "VALIDATE" to "Compare installed readings and document assumptions.",
            "Positive modeled margin" to "Verify field performance and availability conditions.", "Possible obstruction" to "Inspect terrain and first Fresnel zone assumptions."),
        "expanded-guide-network" to guide(
            "LOCAL LINK" to "Check interface, address, prefix and gateway.", "PATH" to "Probe local and remote targets where permitted.",
            "SERVICES" to "Compare DNS, routing and the application target.", "ISOLATE" to "Change one variable and preserve before/after evidence.",
            "IP works; name fails" to "Inspect resolver settings and DNS responses.", "Probe timeout" to "Check filtering and repeat; do not infer a failed link."),
        "expanded-guide-cell" to guide(
            "SUBSCRIPTION" to "Select the intended SIM and check permissions.", "IDENTITY" to "Record exposed roles, band, cell and sample age.",
            "QUALITY" to "Compare power and quality for each technology.", "SERVICE" to "Repeat tests on the intended interface and target.",
            "Strong RSRP, poor SINR" to "Investigate quality and repeat under similar conditions.", "Field not exposed" to "Mark unavailable; never substitute zero or guess."),
        "expanded-guide-fiber" to guide(
            "IDENTIFY" to "Record fiber, wavelength, connectors and transceivers.", "BUDGET" to "Compare path losses with transmitter and receiver limits.",
            "INSPECT" to "Follow qualified inspection and cleaning procedures.", "TEST" to "Measure with calibrated equipment and save results.",
            "Unexpected path loss" to "Check connectors, splices, wavelength and test setup.", "Receive level near limit" to "Compare sensitivity and overload specifications."),
        "expanded-guide-poe" to guide(
            "SOURCE" to "Identify injector or switch and available budget.", "PATH" to "Inspect cable and account for power lost along it.",
            "LOAD" to "Include device peak demand and power negotiation.", "VERIFY" to "Compare a known-good source and preserve results.",
            "Device restarts" to "Check source events, load peaks and cable condition.", "Budget exhausted" to "Compare allocation with per-port and total limits."),
        "expanded-guide-comparison" to guide(
            "QUESTION" to "Define the test and success criteria.", "BASELINE" to "Record repeatable points, equipment and conditions.",
            "CHANGE" to "Document one change and repeat the same tests.", "COMPARE" to "Separate results, missing data and alternate explanations.",
            "Conditions changed" to "Qualify the comparison or collect another baseline.", "Metrics improved together" to "Report correlation; investigate before claiming cause."),
        "expanded-guide-spectrum" to guide(
            "CONFIGURE" to "Record antenna, gain, range and bin width.", "COLLECT" to "Repeat receive-only captures across time or place.",
            "COMPARE" to "Review persistence and service symptoms together.", "REPORT" to "Preserve settings, limitations and unresolved leads.",
            "Visible spectral peak" to "Record frequency and persistence; do not infer identity.", "Uncalibrated SDR" to "Treat power as relative and compare consistent settings.")
    )

    fun forEntry(id: String): Guide? = entries[id]
}
