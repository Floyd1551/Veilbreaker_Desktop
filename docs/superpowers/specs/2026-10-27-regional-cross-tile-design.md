# Regional cross-tile terrain assessment

This increment follows the approved regional-pack workflow. A path near Huntsville can cross adjacent USGS terrain tiles. The operator chooses **Use installed path coverage** in the existing path-assessment dialog. Veilbreaker selects up to 16 installed local terrain packs whose declared raster bounds intersect the path envelope. The existing single-file path remains available.

The sampler uses one geodesic and common sample spacing derived from the finest selected raster. It accepts only tiles with matching declared vertical datum and units, hashes each file against its installed manifest, and prefers the finer raster where valid cells overlap. A no-data cell may fall through to another selected tile; otherwise the sample stays missing. Any missing sample keeps the clearance assessment incomplete. It never fills a gap by interpolation.

Each result records every tile's source, source date, bounds, checksum and number of samples used. The report shows these per-tile records and the count of missing samples. A tile's bounds are not a guarantee of complete data within the rectangle. Physical structure records remain separate from terrain and serving-cell identity.

This is a local multi-raster sampler, not a merged DEM file or a nationwide tile catalog. The operator must prepare all required products before going offline and confirm each product's vertical datum and units. A path remains limited to 100 km and 4096 sample points.
