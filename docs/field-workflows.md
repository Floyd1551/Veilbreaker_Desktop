# Managing field work (0.33.0rc1)

## Diagnostic workspace
Clear workspace clears the displayed run, charts, report tabs, Android input and retry state. It preserves settings, collector selections and saved evidence, and is disabled during collection. Open a saved test from Run history to reload it.

Phone RF findings and hypotheses now appear in the main assessment with receiver labels. The overall service-health score still describes desktop measurements; phone RF does not prove desktop connectivity. Latest exposed values are separate from freshness: unknown-age, repeated, and older-than-10-second samples are explicitly qualified. Ten seconds is a display freshness policy (two minimum USB request intervals), not a modem guarantee. LTE/NR cells remain separate and raw captures remain available.

SDR reports describe observed frequency activity and first-to-last matched-sweep variation. Baseline anomaly reasoning requires recorded receiver, frequency coverage, bin width and gain compatibility. Always retain identical antenna placement for a meaningful comparison. Relative power, a band-plan match or elevated activity alone cannot establish harmful interference or identify a carrier.

## Tests and reports
Run history supports opening, viewing, exporting and deleting a selected test. Delete moves the test out of active history and future baselines into Trash; evidence stays on disk for restoration. Trash / restore brings it back. This is recoverable organization, not disk-space reclamation. External captures and exported copies are untouched.

Tests referenced by an active survey or a confirmed case cannot be deleted alone. Open the owning survey to manage its tests. Confirmed-case evidence is retained. Restore refuses conflicts rather than replacing changed evidence.

## Site Surveys
Open Site surveys to see a searchable Open / Completed list. Click a survey to see attributes, tests, reports and actions. New survey opens the builder; Save survey records the plan without starting a test. Run next starts acquisition using the saved configuration, with manual progression by default.

Configure edits the name, notes and progression; applying current Settings changes only unrun tests. Add tests appends to the selected survey, up to 20 total. Site is fixed and each completed measurement retains its original settings. Complete survey records operator completion independently of collection outcomes. Unrun, failed and partial tests remain identified; Reopen allows further work.

Delete survey defaults to retaining its tests in Run history. The optional owned-test choice also removes eligible tests; shared and case-referenced tests stay available. If a retained test is later independently removed, restore that test before restoring the survey.

GPS and direct phone attachments to survey queues remain future work. Physical phone/SDR qualification is separate from automated tests.
