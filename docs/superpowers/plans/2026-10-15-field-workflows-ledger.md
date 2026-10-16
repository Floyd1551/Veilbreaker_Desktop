# Execution ledger
Approved design and three plans; native execution began October 15, 2026.
Branch: codex/field-workflows; base 680645d.
Ruling: retain the active checkout on a feature branch because it contains the established build environment and no unrelated modifications.
Ruling: use transactional tombstones for recoverable removal; files stay intact, avoiding cross-filesystem rollback failures.

Implemented diagnostic receiver findings/hypotheses and workspace reset; library tombstones and restore UI; survey landing/detail, draft creation, append/configure/lifecycle and recoverable removal.
Ruling: use existing cellular RF rules per receiver and source-labelled hypotheses, retaining desktop scores rather than averaging unrelated receivers. RSSNR/CSI findings retain their own measurement names.
Ruling: samples older than 10 seconds (two minimum USB polling intervals), repeated samples and unknown ages receive explicit qualifiers; latest exposure is distinct from currentness.
Ruling: reuse existing SDR report and main-engine interfaces instead of a second aggregate assess_sdr interface. Shared capture-context qualification blocks unqualified baselines; report observations add relative activity and matching-sweep variation.
Ruling: tombstoned artifacts remain in place; this release supports organization/restore, not disk reclamation. Restore checks original records and all survey dependencies.
Ruling: native implementation used consolidated source commits after interdependent tests; no per-task subagent implementation. Independent review found scenario propagation, restore dependency and sample-freshness defects; fixed with regressions.
Verified initial full suite: 175 tests; focused receiver freshness regression subsequently passes (4 tests). GUI layouts inspected offscreen with Windows fonts. Final packaging verification follows.

Final source validation: 176 unittest tests passed. Independent review findings addressed; final survey detail screenshot inspected with report actions near the top. Hardware qualification not performed.
