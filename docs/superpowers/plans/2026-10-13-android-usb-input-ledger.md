# USB implementation ledger
Plan: 2026-10-13-android-usb-input.md
Ruling: use existing checkout on a feature branch to preserve local packaging/tooling; no concurrent implementers.
Ruling: endpoint uses authenticated POST for all four commands, including status, so request IDs have one consistent JSON format. No tokens in responses or capture evidence.
Ruling: phone handles collection deadlines locally as well as Desktop, so loss of USB cannot leave indefinite acquisition running.
Pre-flight: companion and Desktop share protocol v1, request_id, session_id, status, optional capture envelope. Capture never contains authentication tokens.
Task 1: in progress.

Tasks 1–3: implemented. Kotlin tests first failed in CI without UsbSession, then passed with implementation. Desktop transport, import and GUI tests pass. Reviewer found Windows discovery, pre-start cancellation, timeout termination, missing per-cell changes and premature window-close issues; regression tests and fixes applied. GUI test placement corrected so new attachment and close tests are discovered.
Ruling: prefer modern ADB devices --proto-text connection_type USB because Windows does not consistently expose usb: bus paths. Legacy fallback requires explicit usb: evidence.
Task 4: packaging and documentation in progress; no ADB executable on PATH, so no physical-phone qualification is claimed.

Verification: full Desktop release build passed 155 tests, frozen CLI selftest, Unicode worker/evidence verification and six-page GUI smoke checks. Android CI run 38413020530 passed Kotlin unit tests, APK assembly and both snapshot/session contract validation. Downloaded artifact digest verified; APK SHA-256 b2b97164c11623f2ad3d6bbe6c5e1ac6fa665318bda8d19b9d15ea9a975f6403. Physical USB qualification remains outstanding, explicitly documented.
