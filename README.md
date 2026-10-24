# Botanical Climate Data — public collector (bootstrap v0.1)

A public, botanically agnostic climate-data pipeline with a stable 0.25° grid, land-centre screening, monthly climate summaries, versioned and checksummed outputs, and resumable tile processing.

**Scientific warning:** The current bootstrap source is WorldClim 2.1 (1970–2000 monthly normals). It is **not** a source suitable for exact C3d v1.0 botanical classifications (1991–2020 daily fields, frost extremes and crop-window reliability). Do not use these data to claim lemon frost survival, annual crop success or exact botanical affinity. The first priority after the collection machinery is tested is a 1991–2020 climate adapter and extreme-risk layers.

## Quick start

```bash
python -m pip install -e ".[test]"
pytest -q
bcm-climate run --max-tiles 1
bcm-climate verify
```

The first run downloads the WorldClim 2.1 10 arc-minute ZIP archives and a Natural Earth 1:110m land mask. Each run processes at most one new 5° × 5° tile from `config/plan.json`, writing `published/tiles/<id>.json.gz` and updating `published/manifest.json`.

The pilot is limited to three tiles covering coastal British Columbia, Portugal and the northern Andes. **No global plan is enabled.**

## Scheduled processing

The GitHub Actions workflow is **manual-only** until one real provider run and output audit succeed. If and when approved, add a daily `schedule` trigger to the workflow. The public collector does not include botanical rules or proprietary model code. The private atlas will run analysis independently, not in this workflow.

## Contract

`bcm-climate-monthly-v0.1` includes grid coordinates, twelve monthly means of daily average/min/max temperatures, monthly precipitation, quality flags and source SHA256 hashes. Missing frost extremes, ET0 and crop reliability remain null. Ocean-centred cells are omitted using a coarse land mask. The output cannot be silently treated as exact C3d input.

Check source licence and attribution before wider redistribution. Archive immutable source versions separately when sources change.

Sources: [WorldClim](https://www.worldclim.org/data/worldclim21.html) · [Natural Earth](https://github.com/nvkelso/natural-earth-vector) · [TerraClimate](https://www.climatologylab.org/terraclimate.html).

## 1991–2020 monthly climate profiles (v0.2)

A separate, strictly labelled 1991–2020 TerraClimate collector uses full NetCDF monthly climatology files (tmin, tmax, ppt, pet). Run with `bcm-climate-19912020 run --max-tiles 1` after installing `.[terra,test]`; verify using `bcm-climate-19912020 verify`. Results go to `published-19912020/` and never overwrite the older WorldClim pilot in `published/`. These are still not exact daily C3d botanical inputs. See `docs/19912020-contract.md`.
