# Veilbreaker product direction

Build a dependable local diagnostic companion for Windows and Linux: capture a problem, understand what the evidence supports, choose the next measurement, and compare results after a change. Keep the CLI and desktop on one engine. Missing measurements remain unknown. Consumer presentation follows reliable workflows.

## Phase 1 — Trust the diagnostic record (in progress)

Delivered first increment, 0.10.1rc1: new evidence ZIPs include a versioned SHA-256 manifest, application version and run/site/scenario metadata. Verify from CLI or desktop Tools. Detect changed, missing, extra and duplicate files; label older bundles unverified. Hashes establish consistency, not author authenticity.

Next: collector outcomes and timings, visible progress, explicit partial acquisition, requested-versus-collected measurements, imported metric provenance, cancellation and disconnect recovery. Preserve saved-run compatibility.

Exit criteria: unavailable requested hardware cannot appear as successful acquisition; measurements have a source; cancellation leaves no worker behind; evidence reopens and verifies; device-failure fixtures pass.

## Phase 2 — Dependable hardware workflows

Start with the working HackRF: discovery, bounded receive-only presets, capture settings, repeated spectra, and before/after comparison. Preserve raw CSV and acquisition logs. Distinguish relative RF power from calibrated measurements and protocol identification. Then qualify cellular modems and Starlink with actual hardware and sanitized fixtures.

Exit criteria: connect/disconnect, busy device, timeout and missing dependency flows work on qualified hardware; captures reproduce their displayed summaries. Transmission and firmware modification are outside this roadmap.

## Phase 3 — Guided investigations

Replace raw JSON for common settings with validated forms. Guide users through site/connection selection, readiness, capture, evidence review, suggested tests, recording a change, and comparison. Add searchable history, baseline trends and confirmed-case management. Retain advanced configuration.

Exit criteria: complete and reopen a before/after investigation without CLI commands or JSON editing; comparable measurements and missing data are explicit; reports explain uncertainty.

## Phase 4 — Platform qualification and deeper diagnostics

Qualify Linux desktop/CLI/install/uninstall natively and Windows on a clean machine. Improve Windows measurements across locales. Add explicit interface selection and binding before multi-WAN comparisons. Qualify throughput with real iperf3 servers. Split collectors, reasoning and persistence behind regression coverage as workflows grow. Define a versioned Mobile import format before synchronization.

Exit criteria: reproducible installers, documented OS/device matrix, native test evidence for supported platforms, comparisons measure the intended link, upgrades preserve data. Linux qualification remains pending; cross-platform source alone does not establish it.

## Phase 5 — Consumer application finish

After reliability gates pass, refine navigation, language, onboarding, typography, spacing, empty/error/loading states, spectrum interactions, reports and visual identity. Check keyboard access and accessibility. Decide signing and update distribution before broad release.

Exit criteria: representative users can install, capture a useful diagnostic, understand its limits and share a report without coaching; common failures have clear recovery steps; supported screens and installers pass visual and functional checks.

## Delivery discipline

Ship small versioned increments with tests and release notes. Preserve evidence, backups and existing installations. Distinguish synthetic tests, live hardware tests and platform qualification. Resolve acquisition reliability before expanding feature breadth. One delivered increment does not complete its entire phase.
