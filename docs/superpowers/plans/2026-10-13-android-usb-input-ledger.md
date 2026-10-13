# USB implementation ledger
Plan: 2026-10-13-android-usb-input.md
Ruling: use existing checkout on a feature branch to preserve local packaging/tooling; no concurrent implementers.
Ruling: endpoint uses authenticated POST for all four commands, including status, so request IDs have one consistent JSON format. No tokens in responses or capture evidence.
Ruling: phone handles collection deadlines locally as well as Desktop, so loss of USB cannot leave indefinite acquisition running.
Pre-flight: companion and Desktop share protocol v1, request_id, session_id, status, optional capture envelope. Capture never contains authentication tokens.
Task 1: in progress.
