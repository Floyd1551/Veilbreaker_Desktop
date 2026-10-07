# Offline spectrum reference

The default U.S. reference contains the 154 entries supplied by the project owner on October 6, 2026. The supplied CSV and JSON were checked for equivalent content. Descriptions, carrier associations, and source URLs are preserved as supplied annotations, not independently verified facts. Three GNSS center-frequency entries are rendered as markers, without invented bandwidth. Entries beyond the connected receiver’s frequency range remain reference information and do not expand hardware capabilities. A separate basic FCC reference is available in the legend; its selected ranges were checked against eCFR on October 6, 2026. Neither is a complete allocation table. Each entry carries its source. Frequencies may have additional users; labels are expected uses, never detected protocol identities.

Basic reference sources: [47 CFR 15.247](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-C/section-15.247), [15.407](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-E/section-15.407), [22.905](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-22/subpart-H/section-22.905), [24.229](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-24/subpart-E/section-24.229), and [27.5](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-B/part-27/subpart-A/section-27.5).

Use **Diagnostics → Spectrum → Band legend / import**. Imports replace the selected reference after validation; they do not modify recorded measurements. Restore supplied U.S. reference returns to the full supplied plan; Use basic FCC reference selects the smaller eCFR-sourced reference. Selection persists as `band-plan.json` inside the application data folder. Reports embed the selected reference so an exported interpretation can be traced later.

CSV (UTF-8, MHz):

```csv
min_mhz,max_mhz,label,service,source
2400,2483.5,Site reference,Expected use,Your reference citation
```

JSON:

```json
{
  "name": "Site reference",
  "region": "US",
  "version": "2026-10-06",
  "bands": [
    {"min_mhz": 2400, "max_mhz": 2483.5, "label": "Site reference",
     "service": "Expected use", "source": "Your reference citation"}
  ]
}
```

Required row fields: `min_mhz`, `max_mhz`, `label` (or `band`). `expected_use` is accepted as an alias for `service`. A top-level JSON array of rows is also accepted, matching the supplied files. Optional service/source defaults clearly identify user-supplied information. JSON metadata is optional; CSV uses the filename as the reference name and marks its region Custom. Sources are shown as text, never executed or fetched. Up to 1000 bands and 1 MiB per file. Limits must be finite numbers with `0 <= min <= max <= 1000000`. Labels allow 120 characters; other text allows 500. Overlaps are allowed. Range lookup includes the lower bound and excludes the upper bound. Equal bounds define a center-frequency marker, matched at that frequency only. Narrow labels are elided on the chart; the legend retains full details.

SDR reports use actual CSV bin intervals for coverage, not spacing inferred from surviving bins. Coverage means frequency coverage across the capture; it does not verify every requested sweep completed. Recorded success means the acquisition metadata records exit code zero. The estimated floor is the median of the lowest 20% of bin medians (at least one); activity is the fraction of observed bin medians above that estimate plus 10 dB. These are uncalibrated descriptive statistics and can be biased by wideband signals. They do not identify interference or measure time occupancy.


## Advanced carrier associations

Version 0.20.1rc1 adds optional `carrier`, `direction`, and `association_note` fields to imported and bundled entries. The bundled advanced plan separates general carrier association from radio direction: uplink (device to tower), downlink (tower to device), supplemental downlink, or TDD (both directions sharing the range). Non-cellular services are marked separately. Existing custom selections remain selected; use **Apply advanced U.S. plan** to activate the new default for an existing profile.

Associations are extracted from the supplied descriptions, including historical qualifications. T-Mobile n71/n25/n41 context was cross-checked against [T-Mobile network frequencies](https://www.t-mobile.com/support/coverage/t-mobile-network). Additional carrier references include [Verizon network extender bands](https://www.verizon.com/content/dam/support/pdf/user_guide/verizon-4g-lte-network-extender3-enterprise-v81-user-guide.pdf) and [AT&T supported network bands](https://www.att.com/product-compare/prepaid-phone-compare/). These references do not establish the operator of a signal captured at a particular site.

For explicitly requested untested local builds, `python tools/build_release.py --skip-tests` records `passed: false` and `tests_skipped: true` in the manifest. `build-installer.ps1 -SkipBuild -AllowUntested` permits packaging that result. Default release and CI behavior still runs all checks.


## Band-level survey exports

The SDR report includes every positive-width reference band overlapping a readable capture. Coverage uses the union of actual captured CSV intervals, clipped to the reference band. Full-band coverage divides by the entire reference bandwidth; requested-overlap coverage divides by its intersection with the requested sweep. Power statistics use only bin centers within the band. A narrow band may have interval coverage but no bin centers at coarse resolution; its power stays unavailable. Frequency markers are excluded. Overlaps share bins, so do not sum their statistics.

The CSV preserves capture status, receiver settings, CSV source/hash, and reference version for comparison outside the app. Text cells starting with spreadsheet formula characters are escaped; numeric power values remain numeric. Missing/unreadable captures have no CSV measurement rows; the HTML/JSON report retains their failure notes. Use compatible receiver settings and antenna placement when comparing relative measurements.
