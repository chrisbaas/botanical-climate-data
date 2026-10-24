# E1 climate source engineering — 24 October 2026

## Outcome
The existing TerraClimate integration was ahead of the assignment snapshot. Preserve it: BC and Portugal were already published on main. E1 independently downloaded the same source bytes, reproduced BC byte for byte, and produced a separate 16-cell Colombian test tile in `published-e1/`. All 16 profiles are present and carry a precipitation scientific hold. No prior published file is modified.

The pre-existing schedule and push triggers were removed from main in commit `1dd57ef43cbd360d939457f49bd9010a538b66ce`. Collection remains manual. This development branch adds source identity and metadata guards, bounded tile limits, resume integrity checks, diagnostics, and the real test tile.

## Source and access
Use the four 1991–2020 TerraClimate monthly climatology NetCDF files from HTTPS THREDDS fileServer, as listed in `evidence/e1/source-catalog.json`. This companion catalogue records URLs, SHA256, sizes, dimensions, units and packing. The adapter pins all four file hashes and the land mask. Changed bytes require a reviewed source version, not automatic acceptance.

NCSS climatology metadata still returned HTTP 200 with zero bytes. Adding `time=all` returned HTTP 400. A 12-month, 2×2 OPeNDAP ASCII subset worked (947 bytes, 3.32 seconds). The files exist and HTTPS works; the failure is specific to the NCSS climatology path. Non-CF month coordinates (`units=months`, `calendar=months`) are a plausible cause, not an established server-side diagnosis. No endless retries or fallback to unrelated years.

Source arrays have dimensions time/lat/lon = 12/4320/8640; months 1–12. netCDF4 applies scale 0.1 and offsets −73°C for temperature and zero for moisture, masking fill values. Values are nearest native (~1/24°) samples at target 0.25° centres, not area averages. Native coordinates are validated. The 1:110m land mask is approximate.

Mean temperature is explicitly estimated as (monthly mean daily Tmin + Tmax)/2. PET is labelled TerraClimate reference ET, not interchangeable with another ET0 product. Historical extremes, frost, year-to-year drought and terrain elevation remain unavailable. The source generation is not established by global file metadata (empty); do not label these files v1.1 or mix generations. The provider warns against mixing v1.0 and v1.1.

TerraClimate is distributed as CC0; Natural Earth is public domain. Attribute Abatzoglou et al. (2018), DOI 10.1038/sdata.2017.191, and the source catalogue. See the distribution licence links in the catalogue. No botanical rules or private reference material are included here.

## Verification and measured costs
15 offline tests passed locally. Existing v0.1 and v0.2 published archives verify. The first independent E1 acquisition made five GET requests: four climate files (451,133,926 bytes) plus land mask (138,160 bytes), about 31.19 seconds total request wall time. No annual global time-series archive was fetched.

Cached source initialization (including hashes/metadata): 0.61 seconds. BC regeneration: 0.79 seconds, byte-identical. E1 16-cell processing: 0.53 seconds. Completed-tile repeat: 0.00062 seconds, zero new requests or writes. Peak audit process RSS: 166,060 KiB (~162 MiB). E1 output: 3,848 compressed bytes (240.5/cell); older larger BC/Portugal outputs are ~151–162 bytes per retained cell including missing records. Manifest overhead is additional. Timing varies with host and source layout.

Prior hosted evidence: [first collection](https://github.com/chrisbaas/botanical-climate-data/actions/runs/40113253081), [second collection](https://github.com/chrisbaas/botanical-climate-data/actions/runs/40113795713). First hosted collection command took ~6.6 seconds excluding dependency setup/cache save. E1 measurements above were made locally, not claimed as a new hosted run.

Global planning ceiling: 1,036,800 grid positions, 2,592 five-degree tiles. Using 150–241 bytes/cell gives ~156–250 MB even if every position were retained; actual land output is smaller but unmeasured. Extrapolating ~0.8 s/tile gives ~35 minutes of sampling alone, not an operational forecast: coastlines, missing data, polar coverage, repeated manifest verification and runner startup differ. One tile/day could take up to 7.1 years over the full rectangular tile grid. Cache loss costs another ~451 MB, whereas a reused source cache avoids provider downloads. A no-cache run for every tile would transfer ~1.17 TB: undesirable.

Standard public GitHub-hosted runners are currently free and the ~0.45 GB source cache fits the documented 10 GB repository allowance. This is a credible $0 small-pilot architecture, not a proven global SLA. No paid resources provisioned. Private computation is independent of Actions. See https://docs.github.com/en/billing/concepts/product-billing/github-actions.

## Storage and scientific gates
Cache the original NetCDF files locally or in the existing Actions cache; never commit them into ordinary Git history. Caches can be evicted and upstream files can change. Hashes ensure detection, not perpetual recoverability. A separately approved release-asset snapshot is a possible durable free archive; none was uploaded in E1. The compact derived tiles remain in Git.

Seven diagnostic city profiles are in `evidence/e1/climate-checks.json`: Vancouver, Lisbon, Manaus, Bogota, Pereira, Winnipeg and Riyadh. Their broad seasonality is plausible. This is a sanity check, not station validation. Colombia remains on hold; the product lineage is insufficient to claim an independent resolution of earlier precipitation anomalies.

Not ready for unrestricted unattended collection. Review the source-generation uncertainty, coastal missing profiles (4 BC, 14 Portugal), and regional quality holds first. If PM accepts an explicitly experimental bounded pilot: one 5° tile per manual/daily run, 25-minute timeout, fixed approved plan, same versioned cache, no automatic immediate retries. Monitor Actions failures, manifest coverage and hashes; pause by removing schedule/disabling workflow. Do not activate this recommendation without approval. No global plan was added.

## Reproduction
```
python -m pip install -e '.[terra,test]'
python -m pytest -q
python scripts/e1_verify_live.py
python -m bcm_climate.cli_19912020 verify --output published-e1
```
The audit reuses source files and completed tiles. It overwrites audit measurements on rerun (new_tiles becomes zero); committed evidence records the first E1 run. Outputs in `published/` and `published-19912020/` stay unchanged. See the private consumer handoff separately; public code remains climate-only.
