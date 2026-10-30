# Live phone cell groups in survey views

In a survey map or floor-plan view, select a **Live phone LTE** or **Live phone
NR** metric. When a live session exposes multiple registered cell groups, use
**Reported cell group** to choose one run and one reported identity. Choices
require a full MCC, MNC, TAC and cell ID, a subscription label, a reported phone
model, and at least one fresh uncached sample for the metric. Missing identities
and ambiguous duplicate groups are not offered. The cellular report retains the
original evidence, including any omitted or incomplete groups.

The selected value is a median of fresh uncached samples within that run, or a
single fresh sample when only one is available. The detail shows the receipt
window, sample count and reported cell identity. The result is a run-level
summary, not a reading at each map coordinate. Reported cell IDs do not locate
physical towers or DAS antennas.

Each explicit option is scoped to one run. A phone model and subscription label
do not identify a physical receiver. Automatic coloring is suppressed when it
would compare live values from multiple runs without a verified receiver
identity; select a group to inspect one run at a time. Preserve equipment and
test-condition notes when comparing visits.
