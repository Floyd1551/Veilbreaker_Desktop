# Offline cell matching and terrain paths

Available in 0.37. Open a diagnostic map or **Site Surveys → open survey → Map survey
GPS**, then choose **Cell references / assess path…**. Everything in this workflow
uses local reference/elevation files. The app does not download tower databases or
send captured cell identities to a provider.

## Import and match

1. Obtain an authorized full OpenCellID country export from
   https://docs.opencellid.org/docs/downloads/overview, or prepare operator JSON below.
2. Enter the source, license and dataset date. Import CSV, CSV.GZ or operator JSON.
   Review accepted/rejected/unsupported counts, then **Use selected reference**.
3. Choose a saved test and **Match serving cells in selected test**. The test must
   contain its original Android capture. Identity matching works without GPS;
   distance, bearing and path assessment require qualified same-observation GPS.
4. Select a candidate row. **Show selected bearing** draws the receiver in teal,
   reference in amber, and a dashed bearing line. This does not establish LOS.
5. Use **View context report** or **Save context to survey**. The report includes
   identities, measurements, candidates and source attribution. For a standalone
   diagnostic, save JSON or save HTML from the report viewer.

The OpenCellID adapter supports LTE and NR full identity: radio, MCC, MNC, TAC
and ECI or NCI. It accepts headered and headerless exports. It does not identify
sites by PCI, SIM-carrier name, or nearest mast; matching requires the full identity.
Conflicting coordinates remain visible as conflicting references. Identical
coordinates may have multiple source records. OpenCellID estimates are not surveyed
physical structures. Reference sample count and provider range are context, not
certified positional accuracy. Missing references do not mean the network is bad.

Only explicitly registered cells are matched. GPS/modem offsets and sample ages
remain in context; old modem evidence does not become a current observation simply
because location was captured recently. The first 200 registered observations and
up to 200 candidates per test are retained; omitted/limit states are explicit.
The table displays the selected test; saved context can retain multiple matched tests.

Import limits: 20 million rows, 8 GiB decompressed input, 64 KiB records. Operator
JSON is limited to 8 MiB and 10,000 records. Daily diffs are rejected. Import runs
in a cancellable worker and never activates a partial snapshot. Cancellation or
failure preserves the previous active dataset. Deactivation preserves local files;
reference archives live under application data `cell-references`.

### Operator reference JSON

Use real documented identities and coordinates. The example is intentionally
synthetic and must not be treated as a real site:

```json
{
  "schema_version": 1,
  "records": [{
    "radio": "LTE", "mcc": "310", "mnc": "260",
    "tac": 42, "cell_id": "1234",
    "lon": -96.8, "lat": 32.8,
    "source": "Synthetic example — replace with your documented source",
    "verification": "operator-entered"
  }]
}
```

`operator-verified` is also accepted and displayed as the operator's assertion;
Veilbreaker does not independently verify it. NR uses full NCI and TAC, with no
guessed gNB bit split. Preserve evidence supporting any physical-site association.

## Terrain and LOS

Select a candidate with qualified receiver GPS and choose **Assess selected path…**.
Choose a local single-band GeoTIFF, enter its source, vertical datum and elevation
units, and supply both antenna heights **above local ground**. Do not enter phone
altitude or assume the full tower structure height equals antenna height.

Start with regional USGS 3DEP terrain from https://apps.nationalmap.gov/downloader/.
Confirm the product metadata; supported unit choices are meters, international feet
and US survey feet. The adapter applies stored raster scale/offset and projects
WGS84 endpoints into the raster CRS. The initial adapter uses one self-contained
GeoTIFF (up to 8 GiB). For paths across several tiles, prepare one compatible
regional mosaic outside Veilbreaker. VRT, remote paths and external raster sidecars
are unsupported. Missing coverage remains incomplete; it is never filled with zero.

Supply an exact frequency in MHz for first-Fresnel-zone assessment, or leave it
Unknown for geometric assessment only. Choose geometric Earth (k=1) or explicitly
assumed 4/3 effective Earth radius. Confirm the inputs and calculate. The profile
shows terrain plus Earth bulge, antenna path, and the required 60% Fresnel lower
boundary. Results distinguish sampled obstruction, no sampled obstruction and
incomplete coverage. Limit: 100 km and 4096 samples; excessive resolution demands
produce an explanation instead of silently reducing sampling below the target.

**Keep assessment in context**, then save the cell context to the survey. Changing
inputs disables Keep until recalculated. Reports retain the exact DEM checksum,
endpoint/source uncertainty, heights, frequency, model, sample spacing, numeric
profile and embedded image. New evidence exports include the context JSON and
separate terrain PNGs in their manifest. Reopening reports requires no DEM or
reference database. Existing captured evidence and earlier exports stay unchanged.

These are conditional, sampled, bare-earth calculations. Buildings, trees, sub-pixel
obstacles, atmospheric variation and antenna patterns are not modelled. An estimated
cell coordinate makes the selected endpoint uncertain; no sampled obstruction does
not guarantee optical visibility, radio coverage or connectivity.

## Source installation and validation

Windows installers include terrain dependencies. Source environments use
`pip install -e ".[desktop,terrain]"`; the terrain extra pins rasterio 1.4.4 and
pyproj 3.7.2. Cell matching remains usable without those GIS packages. Linux source
support is retained; Linux native packaging has not been validated on this host.

Numerical and workflow tests use synthetic references/DEMs. A small real USGS
3DEP Dallas extract was sampled as an adapter check. The supplied MCC 311 OpenCellID
country export is available for local cell-reference testing. It does not cover all
US MCCs, and community-estimated positions are not verified physical structures.
No surveyed tower/antenna endpoint was supplied, so serving-site and field LOS
validation remain outstanding. The supplied application does not include a tower
inventory or a national DEM.
