# Veilbreaker Desktop reconstruction

Updated September 30, 2026. The supplied backup resolves the missing-source blocker.

- All 46 original artifact checksums matched the supplied inventory.
- Desktop 0.9.3 multimodem is the recovered baseline; original files remain untouched.
- Version 0.10.0rc1 adds the native desktop workspace around the retained CLI/engine.
- Windows/Linux source and build paths, Windows installer, and Linux installation tooling are implemented. Verification is recorded separately.

Read [the complete inventory and architecture](PROJECT_INVENTORY.md), [installation/build instructions](../README.md), [verification results](VERIFICATION.md), and [next milestones](ROADMAP.md).

Working source is in `src/veilbreaker`. Original backups are preserved outside the checkout in the sibling `Veilbreaker-Local-Archive` directory. Local diagnostics and generated releases are excluded from Git.
