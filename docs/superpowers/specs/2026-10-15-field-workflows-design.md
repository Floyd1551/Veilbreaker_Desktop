# Field workflows and diagnostic evidence

Date: October 15, 2026
Status: Scope approved; written design awaiting review.

## Intent

Veilbreaker is a technical field application. An operator must be able to collect evidence quickly, understand the resulting diagnostics, and manage tests and surveys without navigating a crowded workbench. Retain comprehensive evidence and offline HTML reports. Existing saved runs and surveys remain readable. Documents in this increment means generated tests, reports, and evidence bundles, not arbitrary office attachments.

## 1. Diagnostic evidence

The current live Android path evaluates individual cells in collector notes but passes session counts to the separate phone report. The main desktop assessment therefore cannot represent the available phone RF evidence correctly. Introduce structured receiver assessments shared by the summary, findings, report viewer, and exports. Each phone assessment identifies its subscription, radio, stable cell identity, sample time, age, and source. Preserve the original capture and per-cell statistics.

Use the latest exposed measurements per cell with their actual timestamps; never silently describe an earlier reading as current. Distinguish unavailable, stale/cached, and not collected. LTE RSRP/RSRQ/RSSNR and NR SS/CSI measurements retain their identities and units. Missing-field messages describe the receiver concerned. A valid phone measurement satisfies phone RF availability, but cannot satisfy measurements required for an unrelated desktop modem. Do not average cells, select the strongest cell as representative, or infer that desktop throughput used the phone connection. Source findings appear in the main Findings view and reports with clear receiver labels; technical raw details remain available.

SDR assessment will expose observed concentration, occupancy and temporal changes with supporting measurements and specific next tests. Relative power remains uncalibrated. Baseline comparisons require compatible frequency coverage, bin width and receiver/gain settings; unavailable compatibility metadata means comparison is unqualified and cannot support a confident baseline anomaly. Band-plan matches provide frequency/service context, not proof of carrier identity or harmful interference. Distinguish an observed RF change from a diagnosed service fault. Preserve the existing plots and waterfall.

Keep assessment rules deterministic and explainable. Tests cover weak/healthy/missing phone readings, multiple cells, cached readings, LTE/NR separation, source isolation, SDR changes, and incompatible baselines. No new RF transmission or hardware access is required.

## 2. Clear diagnostic workspace

Add a visible Clear workspace action beside the diagnostic actions. When idle, it clears the current payload/run identity, all result tabs (including cellular, spectrum and SDR), collector output, progress/result messages, selected input-file reference, Android attachments and transient pairing credentials, and retry context. Restore meaningful empty-state text and disable actions requiring a displayed result. Preserve user configuration, collector selections, site/scenario settings, and all saved runs, reports and survey data. Clearing is immediate and needs no deletion confirmation. Disable it during acquisition; it is not a cancel action. Loading a saved run afterwards still works normally.

## 3. Test and report library

Evolve Run history into a library with existing search/pagination and a concise selection toolbar: Open, View reports, Export, Delete. Display site, date, scenario, collection/assessment state and survey association where available. Keep advanced comparison accessible without crowding primary actions.

Delete is recoverable removal to an application-managed Trash, not immediate filesystem destruction. A confirmation names the selected test and its associated evidence. Exclude trashed runs from active history and baseline selection. Preserve records and artifacts for restore; no permanent purge is included in this increment. Trash has list and restore actions. Never delete external source captures or exports outside managed application storage. Validate resolved paths before any file mutation. Persist a removal record and make operations retryable so interruption does not orphan evidence or silently lose a database record.

If a run is referenced by a survey or confirmed case, show the dependency and block standalone deletion with an explanation and a route to the owning workflow. Existing confirmed cases retain their provenance. Clearing or deleting the currently displayed unreferenced run also resets the workspace. No automatic historical reanalysis occurs when a run is removed from future baselines.

## 4. Survey landing and detail flow

Site Surveys opens on a searchable list with Open and Completed filters and a New survey action. Rows show name, site, lifecycle, last update, and completed/total test counts. Opening a row navigates to survey detail with a Back to surveys action. Move the existing builder out of the landing page and into New survey/configuration.

Detail contains attributes (name, site, notes), tests with collection and assessment states, in-app reports/comparisons, and grouped actions: Configure, Add tests, Run next/Continue, Complete/Reopen, Delete. Existing manual progression remains the default. Retain the 20-test cap, showing remaining capacity. Completed tests and their original acquisition settings are immutable. Configuration changes apply only to future tests and are recorded per test. Adding tests never silently starts acquisition. Changing site after acquisition is disallowed; create a new survey for another site.

Operator lifecycle (open/completed) is distinct from collection outcome (complete/partial/failed/interrupted). Completing with unrun steps requires an explicit summary and records those steps as not run; it must not turn them into successful measurements. Reopen allows additions and continuation while preserving prior evidence and completion history. Legacy journals map complete collection state to completed lifecycle and other states to open, without rewriting their recorded outcomes. Apply additive journal fields and preserve existing locks and atomic writes.

Survey deletion moves its journal/configuration to Trash. Default is to retain its test runs as standalone history records. An explicit alternative includes exclusively owned test runs, with a count and dependency checks; shared or case-referenced runs remain preserved and are identified in the confirmation. Restore preserves identifiers and links and refuses conflicts rather than overwriting newer data. Running surveys cannot be edited, completed or deleted.

## Delivery order and validation

1. Repair and surface source-specific cellular/SDR assessment; add Clear workspace.
2. Add recoverable library removal/restore and dependency handling.
3. Introduce survey landing/detail navigation and lifecycle actions.

Each increment includes focused regression tests and a GUI smoke check. Verify old fixtures remain readable, cleared workspaces contain no stale charts or input credentials, deletion cannot escape managed storage, interrupted removal is recoverable, shared references survive, and survey completion does not alter collection truth. Final packaging runs the full suite and frozen Windows checks. Physical phone and SDR qualification remain separately reported. Commit finished changes to the user's GitHub repository; do not claim hardware qualification from synthetic tests.

## Exclusions

No GPS/maps, raw baseband decoding, cloud synchronization, arbitrary document editor, permanent purge, new transmission workflows, or wholesale visual rebrand. These do not block the requested field workflow.
