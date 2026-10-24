"""Immutable, provenance-rich 1991-2020 monthly profiles, separate from v0.1 archive."""
from pathlib import Path
import gzip,json,hashlib
from .grid import cells_for_bbox
from .worker import bjson,atomic,gzip_deterministic
SCHEMA="bcm-climate-monthly-v0.2"
DAYS=(31,28.25,31,30,31,30,31,31,30,31,30,31)
def features(p):
    means=[(a+b)/2 for a,b in zip(p["tmin"],p["tmax"])]
    annual_p=sum(p["ppt"]);annual_et=sum(p["pet"])
    return {"annual_mean_temperature_estimate_c":round(sum(a*b for a,b in zip(means,DAYS))/sum(DAYS),3),
            "coldest_monthly_mean_estimate_c":round(min(means),3),
            "warmest_monthly_mean_estimate_c":round(max(means),3),
            "annual_precipitation_mm":round(annual_p,2),
            "annual_terraclimate_reference_et_mm":round(annual_et,2),
            "p_over_terraclimate_reference_et":round(annual_p/annual_et,4),
            "months_precip_below_reference_et":sum(a<b for a,b in zip(p["ppt"],p["pet"])),
            "annual_absolute_minimum_c":None,"frost_frequency":None,
            "annual_crop_reliability":None}
def provenance(source):
    return {"name":source.name,"baseline":source.baseline,"sha256":source.hashes,
            "native_grid_degrees":1/24,"sampling":"nearest_native_to_target_center",
            "generation":"legacy_climatology_generation_not_verified",
            "reference_et":"TerraClimate PET/RET, not demonstrated equivalent to C3d FAO ET0"}
def process(spec,source,out):
    if any(abs(spec["bbox"][i+2]-spec["bbox"][i])>5 for i in (0,1)):
        raise ValueError("Pilot tiles must not exceed 5 degrees per side")
    out=Path(out);all_cells=list(cells_for_bbox(*spec["bbox"]))
    land=[c for c in all_cells if source.land_covers(c.lon,c.lat)]
    profiles=source.sample(land) if land else {}
    cells=[];missing=0;colombia=0
    for c in land:
        p=profiles[c.id]
        if p is None:
            missing+=1
            cells.append({"cell_id":c.id,"lat":c.lat,"lon":c.lon,"status":"missing_source",
                          "monthly":None,"features":None,"quality_flags":["source_nodata"]})
            continue
        f=features(p)
        flags=["monthly_normals_only","no_frost_extremes","no_crop_reliability",
               "reference_et_not_c3d_fao_et0","coarse_land_mask"]
        if -82<=c.lon<=-65 and -5<=c.lat<=13:
            flags.append("colombian_precipitation_independent_check_required");colombia+=1
        cells.append({"cell_id":c.id,"lat":c.lat,"lon":c.lon,"status":"monthly_profile",
                      "monthly":{"tmin_daily_mean_c":[round(x,3) for x in p["tmin"]],
                                 "tmax_daily_mean_c":[round(x,3) for x in p["tmax"]],
                                 "tmean_estimate_c":[round((a+b)/2,3) for a,b in zip(p["tmin"],p["tmax"])],
                                 "precipitation_mm":[round(x,3) for x in p["ppt"]],
                                 "terraclimate_reference_et_mm":[round(x,3) for x in p["pet"]]},
                      "features":f,"quality_flags":flags})
    tile={"schema":SCHEMA,"tile_id":spec["id"],"bbox":spec["bbox"],"grid_degrees":0.25,
          "source":provenance(source),
          "limitations":["Not exact C3d daily inputs","No 30-year extreme-event histories",
                         "TerraClimate RET not proven numerically equivalent to C3d FAO ET0"],
          "coverage":{"grid_positions":len(all_cells),"land_centres":len(land),
                      "ocean_centres":len(all_cells)-len(land),
                      "missing_land_profiles":missing,"colombia_precipitation_hold_cells":colombia},
          "cells":cells}
    z=gzip_deterministic(bjson(tile));p=out/"tiles"/f"{spec['id']}.json.gz"
    if p.exists():
        if p.read_bytes()!=z:raise ValueError("Refusing to silently overwrite changed source")
    else:atomic(p,z)
    return {"file":f"tiles/{spec['id']}.json.gz","sha256":hashlib.sha256(z).hexdigest(),
            "bytes":len(z),"coverage":tile["coverage"],"source":provenance(source)}
def verify(out):
    out=Path(out);m=json.loads((out/"manifest.json").read_text())
    if m.get("schema")!=SCHEMA:raise ValueError("Wrong contract")
    for tid,item in m["tiles"].items():
        raw=(out/item["file"]).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=item["sha256"]:raise ValueError("Tile hash mismatch")
        tile=json.loads(gzip.decompress(raw))
        if tile["schema"]!=SCHEMA or tile["tile_id"]!=tid or tile["source"]!=item["source"]:
            raise ValueError("Tile contract/provenance mismatch")
    return len(m["tiles"])
def run(plan_path,out,source,max_tiles=1):
    if not 1 <= max_tiles <= 3: raise ValueError("Pilot limit is 1 to 3 tiles")
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    plan=json.loads(Path(plan_path).read_text())["tiles"]
    mpath=out/"manifest.json"
    m=json.loads(mpath.read_text()) if mpath.exists() else {"schema":SCHEMA,"tiles":{}}
    if m["schema"]!=SCHEMA:raise ValueError("Cannot mix dataset contracts")
    for item in m["tiles"].values():
        if item["source"]!=provenance(source):
            raise ValueError("Source drift: create a new version, never mix")
    if mpath.exists(): verify(out)
    count=0
    for tile in plan:
        if tile["id"] in m["tiles"]:continue
        m["tiles"][tile["id"]]=process(tile,source,out)
        atomic(mpath,bjson(m))
        count+=1
        if count>=max_tiles:break
    verify(out)
    return count
