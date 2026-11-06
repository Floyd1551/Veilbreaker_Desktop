package com.veilbreaker.companion

/** Supplemental interpretation for the offline field guides. Examples are illustrative, not measured cases. */
internal object ExpandedGuideDetails {
    val sections = mapOf(
        "guide-wifi" to """
            DECISION POINT
            Define coverage and application requirements for the actual clients. Weak signal at a boundary calls for another measured point and a coverage check; strong signal with poor service calls for quality, contention, roaming and backhaul checks before moving an AP. Decide whether the question concerns one client, one BSSID, one floor or a shared network service.

            FIELD EXAMPLE
            A hypothetical client has strong RSSI but a slow transfer near a conference room. Repeat the same transfer nearby and while the room is idle; compare the associated BSSID, channel width, retries or AP-side utilization if available. A nearby scan alone cannot establish the airtime load or the cause.

            DATA QUALITY
            Scan timestamps, permissions, device orientation and client radio capabilities affect comparisons. Distinguish a scan result from the associated connection and negotiated link speed from measured throughput. Mark missing noise and utilization as unavailable; never infer either from RSSI.

            NEXT ACTION
            Record a repeatable walk and known test target. If coverage remains weak, survey candidate placement changes; if service is slow despite adequate signal, inspect AP, wired uplink and server counters. Retest unchanged locations and preserve both results.
        """.trimIndent(),
        "guide-fwa" to """
            DECISION POINT
            Start with a stable baseline and compare candidate positions using the same modem, subscription, test duration and approximate loading. If signal power improves but quality or service degrades, examine band or cell changes, interference and orientation before choosing the strongest reading. Consider both uplink and downlink.

            FIELD EXAMPLE
            An illustrative window position improves RSRP while SINR and upload worsen compared with a second position. Note cell, band and time, then alternate positions several times with the same equipment. The observation supports further investigation; it does not by itself identify an interferer or prove the second position will always be better.

            DATA QUALITY
            Phones and modems may cache samples, switch bands, aggregate carriers or omit serving roles. A crowdsourced tower match can be stale or approximate. Coax loss, antenna pattern and mounting geometry must use actual equipment data; a handset observation is not a calibrated antenna-system measurement.

            NEXT ACTION
            Compare shortlists over representative times, inspect obstacles and install constraints, and document cable length and orientation. After a qualified installation, repeat the baseline tests and keep the original results and unresolved assumptions with the report.
        """.trimIndent(),
        "guide-das" to """
            DECISION POINT
            Agree on the required carrier, test device, floor boundaries and pass criteria with the project team before collection. If an individual point fails, first separate a coverage concern from a quality or service-path concern; repeat the point and neighboring points before proposing an adjustment.

            FIELD EXAMPLE
            In an illustrative corridor, two nearby points share the same cell identity but one has much poorer SINR. Inspect the location and timing, then repeat with the same orientation and subscription. The shared ID does not reveal which physical remote is serving either point and does not establish the cause of the difference.

            DATA QUALITY
            Indoor GPS may be inaccurate or absent. Preserve operator floor-plan coordinates separately from GPS, retain the floor and evidence identifier, and leave a point unplaced rather than guessing. Report omitted metrics and stale samples explicitly; recorded observations of walls or antennas are not sensor measurements.

            NEXT ACTION
            Compare repeat failures with the acceptance criteria and coordinate access to infrastructure counters or calibrated test equipment. Log any retest after an authorized change, include remaining untested spaces and never attribute a point to a remote based on cell ID alone.
        """.trimIndent(),
        "guide-rf" to """
            DECISION POINT
            Treat free-space loss as an ideal reference. If a terrain or clutter obstacle intersects the first Fresnel zone, do not treat a clear straight line on a map as a complete clearance assessment. Decide whether better terrain, a surveyed obstruction or a more detailed propagation analysis is required.

            FIELD EXAMPLE
            A hypothetical link budget predicts adequate received power in free space, yet the path passes through a tree line. Compare a documented terrain profile and seasonal vegetation against the geometry, then measure both directions after installation. The free-space calculation alone cannot quantify that tree loss.

            DATA QUALITY
            Document elevation datum, survey date, antenna heights above the correct reference, center frequency, cable length and receiver mode. Manufacturer peak gain is directional; equipment sensitivity depends on modulation and bandwidth. Missing terrain or vegetation remains unknown, not zero loss.

            NEXT ACTION
            Check regulatory constraints and polarization at both ends, recalculate with measured cable and antenna data, then validate received level and service. If measured results diverge, inspect alignments, connectors and the path before changing the model assumption.
        """.trimIndent(),
        "guide-network" to """
            DECISION POINT
            A failure to reach a gateway suggests investigating the local link and configuration; a reachable gateway with a failed named service warrants separating DNS from routing and application behavior. A successful ICMP response does not prove a TCP or application path works.

            FIELD EXAMPLE
            In an illustrative case a known IP responds but a hostname fails. Record the resolver, compare a second authoritative or approved resolver and note cached answers before diagnosing DNS. If both name and IP work but one application fails, check the intended port, proxy, TLS and server-side health with appropriate authorization.

            DATA QUALITY
            Record interface, target, timestamps and test direction. VPNs, IPv4 versus IPv6, captive portals, DNS caching and server selection can invalidate an apparent before/after comparison. Rate-limited or filtered probes can show loss even while application traffic succeeds.

            NEXT ACTION
            Collect the last known good result and identify the first failing dependency. Escalate with route, resolver and test evidence, minimizing sensitive identifiers in shared reports. Validate the fix against the original symptom as well as the individual dependency.
        """.trimIndent(),
        "guide-cell" to """
            DECISION POINT
            Compare same-technology measurements first. Low reference power can motivate a position test; adequate power with poor quality calls for controlled comparisons of orientation, band, cell, load and service performance. Missing values mean unavailable, not a zero or a failed signal.

            FIELD EXAMPLE
            A hypothetical capture shows an LTE anchor with weak quality and a separately reported NR signal. Record their individual ages and roles, then repeat at a nearby position and against the same service target. Do not assume that the LTE value represents NR, or that the phone reported every aggregated carrier.

            DATA QUALITY
            Select the correct subscription and verify the actual data interface. Android permissions, caching, modem implementation and power-saving policy affect what is exposed; a reported PCI is reused and is not a physical tower address. Throughput depends on more than radio signal.

            NEXT ACTION
            Group results by subscription, technology, band and time; compare repeated samples rather than one snapshot. If a database suggests a site, label it as a candidate and seek independent verification before making a location claim.
        """.trimIndent(),
        "guide-fiber" to """
            DECISION POINT
            Compare measured insertion loss with the documented cable-plant budget and the optics' receive operating range. A low received level can result from a weak transmitter, excessive path loss or a dirty interface; an overly strong signal can exceed a receiver's specified input range.

            FIELD EXAMPLE
            In a hypothetical installation a link is within its modeled distance but the received level is below specification. Confirm the wavelength and instrument reference, inspect and clean connectors using approved procedures, then repeat the loss and receive-power tests. Do not substitute a calculated budget for a measured result.

            DATA QUALITY
            Capture instrument calibration, reference method, wavelength, direction, launch conditions and connector count. Test cords and bulkhead interfaces can contaminate measurements. The receiver's reported optical level may not have the same accuracy as calibrated test equipment.

            NEXT ACTION
            Follow site laser safety and use qualified personnel. If loss remains high, isolate cable sections and test from both ends using appropriate instruments. Preserve actual readings, test conditions and the manufacturer's sensitivity and overload ranges.
        """.trimIndent(),
        "guide-poe" to """
            DECISION POINT
            First establish whether the device is unpowered, restarting or powered but unable to pass traffic. Compare the requested or measured device demand with the source's per-port capabilities and remaining shared budget; check the complete cable path before replacing the radio.

            FIELD EXAMPLE
            An illustrative access point restarts only when additional devices start. Record switch power allocation and event times, then compare demand, startup behavior and budget. This pattern suggests a power investigation but can also reflect cabling or device faults, so use a rated known-good source and cable to isolate the path.

            DATA QUALITY
            A configured allocation is not always actual consumed power. Include cable and connector condition, injector model, negotiated mode and simultaneous load; advertised total capacity may not equal spare power at a specific port. Do not treat an estimated loss as a cable measurement.

            NEXT ACTION
            Use manufacturer specifications and appropriately rated test equipment. Correct the confirmed bottleneck under the site's change procedure, then repeat under representative peak conditions and retain the before-and-after power and service evidence.
        """.trimIndent(),
        "guide-comparison" to """
            DECISION POINT
            Before declaring improvement, check that the two runs address the same metric and purpose. A different device, floor, band, serving cell, target or test duration can explain a change without any improvement in the modified system.

            FIELD EXAMPLE
            A hypothetical after-run has higher download speed, but it used a different server and time of day. Label it as non-comparable and rerun against the original target at a similar load. Show the original values and conditions rather than silently averaging incompatible runs.

            DATA QUALITY
            Track clock and sample age, collection outcome, location provenance, missing values, direction and any changes in hardware or configuration. Keep operator-entered observations distinct from sensor data. Point placement errors and small sample counts can mislead spatial comparisons.

            NEXT ACTION
            Preserve raw runs and the change log. Compare distributions or repeatable points where feasible, include contradictory observations, and state whether the outcome meets the original acceptance criteria. Recommend further sampling if confidence is limited.
        """.trimIndent(),
        "guide-spectrum" to """
            DECISION POINT
            A persistent feature at a consistent frequency warrants a controlled comparison across time and position. First determine whether receiver gain, bandwidth, antenna, bin size or local conditions changed; a difference in settings can create an apparent change in the display.

            FIELD EXAMPLE
            In an illustrative capture a broad feature coincides with degraded network service. Repeat with unchanged receiver settings during a known idle period, record the affected channel and compare several locations. The correlation is a lead, not proof of the source or a measurement of channel utilization.

            DATA QUALITY
            Relative SDR power is generally uncalibrated and depends on gain, sample rate and antenna response. Noise-floor estimates, sweep timing and short bursts can be misleading. Preserve the exact frequency range, configuration and timestamps; do not identify a waveform solely from its shape.

            NEXT ACTION
            Compare captures with independent network and service evidence, then use appropriate calibrated or demodulating equipment and authorized procedures if source identification is required. Keep unresolved candidates and alternate explanations in the report.
        """.trimIndent()
    )
}
