# Physical-structure workflow and 1.0 field gates

Desktop 0.68.0rc1 adds an operator-selected path from a survey map position
to an offline physical-structure reference. Select a qualified recorded location or
an operator-placed geographic point, search installed structure packs, inspect
the record and choose whether to show the bearing or assess the terrain path.
The terrain assessment requires separately entered antenna heights and retains
the structure, terrain, and receiver provenance. Survey assessments join the
existing reference report and are included in survey exports; standalone
assessments can be viewed or explicitly exported as JSON.

The supplied FCC ASR snapshot is a dated inventory of registered structures,
not an authoritative or current inventory of every cellular site. A structure
is not evidence of a serving relationship, carrier, antenna position, or
present condition. Its registered height is not an antenna height. NAD83
positions are shown as approximate WGS84 without a datum transformation.
Missing or partial pack coverage and missing terrain remain visible. A terrain
profile does not account for buildings, vegetation or all RF propagation.
Operator placement remains distinct from recorded GPS evidence.

Before a 1.0 field release, the remaining gates include:

- Validate the entire offline survey workflow in the field, including pack
  installation, positioning, structure selection, terrain availability,
  report reopening and export, and actual antenna-height assumptions.
- Qualify Windows and Linux builds and connected equipment, including failure,
  recovery, large-text and accessibility scenarios.
- Review dataset currency, regional coverage and distribution terms; terrain
  must be prepared for the intended area, and the included cell snapshot does
  not represent every US carrier or tower.
- Decide release signing, update and migration strategy; verify the final
  installer and its lifecycle on clean machines.

Automated and packaged checks do not substitute for these field gates.

## November 19 local-data workflow check

An isolated temporary survey used a public downtown Huntsville fixture position,
two overlapping installed FCC ASR packs and the USGS 3DEP 1/3-arc-second
`n35w087` terrain pack dated 2026-10-20. The pack declares NAVD88 and metre
elevations; its SHA-256 was verified during sampling. A selected structure path
produced 417 terrain samples with no missing samples. Its assessment was saved,
reopened and exported with the alternate structure-pack provenance retained.

The receiver capture and position, 2 m receiver height, 30 m site antenna
height, 1900 MHz frequency and 4/3 Earth factor were test assumptions, not
field measurements. The workflow invoked local search, raster and export
operations with PROJ networking disabled and made no explicit network requests;
the host was not disconnected or monitored. This is a useful integration check,
not a live field test or proof of a serving relationship, real antenna heights,
complete area coverage, physical visibility or radio propagation.

## Windows installer check

On November 19, an isolated-identity test of the 0.69.0rc1 release payload
passed per-user installation and registration, shortcuts, installed CLI and
GUI smoke checks, reinstall with preserved test configuration, and uninstall
with preserved test data. It used a separate validation app identity and did
not replace the existing installation. The initial attempt used an unusually
deep temporary destination and failed on a Windows path-length limit; rerunning
the same lifecycle from a shorter isolated directory passed. This is local
validation of that preview, not a clean-machine or signed-release test.
