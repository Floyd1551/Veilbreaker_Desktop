# 0.38.0rc1 — capture diagnostics and saved survey inputs

The engine now describes patterns within phone and SDR captures, with supporting
counts, source labels and a next field test. Findings appear in the main diagnostic
view, the cellular/SDR reports, and the exported evidence. They do not alter the
desktop health score or claim that a phone RF observation caused a desktop outage.

## Phone patterns

- Repeated weak coverage: at least five independent samples over at least ten
  seconds, with at least 80% at or below -110 dBm RSRP / NR SS-RSRP.
- Recovered quality drop: a middle sample at least 6 dB below both neighboring
  RSRQ samples, or 8 dB below both neighboring LTE RSSNR / NR SS-SINR samples.
  These remain separately named quantities. All three span at most 15 seconds.
- Repeated primary-cell changes: at least three changes within 60 seconds,
  within one SIM and radio technology, using exposed MCC/MNC/full cell ID.
  Secondary-cell changes and optional TAC/channel metadata changes do not count.

Only explicitly registered LTE/NR samples with known age at most ten seconds,
usable identity, increasing modem sample time and no repeated sample timestamp
qualify. Missing signal values and gaps over 15 seconds break sustained sequences.
These are observations at sampled instants, not proof of continuous conditions,
failed handovers, interference or service failure. Analysis is bounded to 128 cell
identities and 64 findings, with omissions reported.

## SDR patterns

At least five reconstructed sweeps with identical, complete, nonoverlapping
frequency bins are required. Capture success and recorded gain, amplifier,
antenna-power and bin-width settings are required in the report workflow.

- Persistent activity: a bin exceeds each sweep's estimated floor by 10 dB in
  at least 80% of reconstructed sweeps.
- Brief activity: the same threshold is exceeded in at most 20% of sweeps.
- Broad power rise: at least six sweeps; the median floor of the last three is
  at least 8 dB above the first three, and at least 80% of matched bins rise 8 dB.

The floor is the median of the lowest 20% of bin powers. Strong broad signals can
bias it. Up to 20 matching frequency intervals per finding are listed. Analysis
uses the waterfall's first 128 reconstructed sweeps and reports truncation.
Sweep order is not calibrated elapsed time; these percentages are not transmitter
duty cycle. Fixed recorded settings cannot establish unchanged physical antenna
placement. Power remains relative and uncalibrated.

## Saved diagnostics in surveys

Run History now offers **Add to survey**. Survey details offer **Add existing
diagnostics**, with search and multiple selection. Original evidence is linked,
not recollected. Duplicate tests and additions beyond 20 are blocked. Completed
surveys must be reopened. Removing a survey with its owned tests preserves linked
diagnostics. See [workflow](existing-diagnostics-in-surveys.md).

Existing evidence bundles are not rewritten. Newly generated diagnostic reports
include capture findings when the underlying phone/SDR evidence is available.
Summary-only metric imports cannot provide temporal evidence.

## Qualification

Synthetic regression coverage exercises sample freshness, missing identity,
SIM separation, optional metadata changes, coverage gaps, persistence, bursts,
floor rises, and report/evidence integration. Physical RF and phone field
qualification remains separate from these software tests.

Final source qualification: 240 tests passed, including regressions for optional
identity metadata, out-of-order primary samples, and repeated cached callbacks.
Independent review identified the latter two primary-cell tracking defects;
both were reproduced with failing tests and corrected before the final rebuild.

The final Windows portable build passed frozen CLI, Unicode worker/evidence,
six-page desktop, offline-map and terrain smoke checks. Its SHA-256 sidecar was
verified against the archive. Linux packaging and live hardware qualification
were not performed for this increment.

Windows installer compilation completed on October 22, 2026; its SHA-256 sidecar
was verified. Installer is ready to install; the existing application was not
replaced during this release.
