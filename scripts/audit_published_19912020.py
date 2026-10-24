"""Read-only quality review of published BC tiles: preliminary, not independent climate validation."""
import gzip,json,statistics
from pathlib import Path
def load(parent):
 m=json.loads((parent/"manifest.json").read_text())
 entry=m["tiles"]["bc-coast-01"]
 tile=json.loads(gzip.decompress((parent/entry["file"]).read_bytes()))
 return tile
older=load(Path("published"))
new=load(Path("published-19912020"))
a={c["cell_id"]:c for c in older["cells"] if c["status"]=="monthly_profile"}
b={c["cell_id"]:c for c in new["cells"] if c["status"]=="monthly_profile"}
assert new["schema"]=="bcm-climate-monthly-v0.2"
assert new["source"]["baseline"]=="1991-2020"
assert new["source"]["name"]=="terraclimate-19912020-climatology"
assert len(b)>=300 and len(b)<=len(a)
assert all(len(x["monthly"]["precipitation_mm"])==12 for x in b.values())
assert all(len(x["monthly"]["terraclimate_reference_et_mm"])==12 for x in b.values())
assert all(x["features"]["annual_absolute_minimum_c"] is None for x in b.values())
assert all("no_frost_extremes" in x["quality_flags"] for x in b.values())
assert all("reference_et_not_c3d_fao_et0" in x["quality_flags"] for x in b.values())
common=sorted(set(a)&set(b))
delta_t=[];ratios=[]
for key in common:
 old=a[key]["features"];fresh=b[key]["features"]
 dt=fresh["annual_mean_temperature_estimate_c"]-old["annual_mean_temperature_c"]
 delta_t.append(dt)
 if old["annual_precipitation_mm"]>0:
  ratios.append(fresh["annual_precipitation_mm"]/old["annual_precipitation_mm"])
print("Old valid",len(a),"new valid",len(b),"overlap",len(common),"missing",new["coverage"]["missing_land_profiles"])
print("Annual temp difference Celsius (min,median,max)",*[round(x,2) for x in (min(delta_t),statistics.median(delta_t),max(delta_t))])
print("Annual precip ratio new/old (min,median,max)",*[round(x,2) for x in (min(ratios),statistics.median(ratios),max(ratios))])
p=[x["features"]["annual_precipitation_mm"] for x in b.values()]
et=[x["features"]["annual_terraclimate_reference_et_mm"] for x in b.values()]
print("New annual P mm (min,median,max)",*[round(x,1) for x in (min(p),statistics.median(p),max(p))])
print("New annual RET mm (min,median,max)",*[round(x,1) for x in (min(et),statistics.median(et),max(et))])
# Large departures need investigation rather than coercion.
if abs(statistics.median(delta_t))>6:
 raise ValueError("Gross shifted monthly temperature values; review source")
if not 0.1<statistics.median(ratios)<10:
 raise ValueError("Gross rainfall unit mismatch")
nearest=min(b.values(),key=lambda c:(c["lat"]-49.25)**2+(c["lon"]+123.12)**2)
print("Sample near Vancouver",nearest["cell_id"],nearest["lat"],nearest["lon"],
      "annual temperature estimate",nearest["features"]["annual_mean_temperature_estimate_c"],
      "annual precipitation",nearest["features"]["annual_precipitation_mm"],
      "annual RET",nearest["features"]["annual_terraclimate_reference_et_mm"],
      "monthly coldest/warmest",nearest["features"]["coldest_monthly_mean_estimate_c"],
      nearest["features"]["warmest_monthly_mean_estimate_c"])
print("PASS: 1991-2020 data are internally consistent and broadly in range of 1970-2000 norms.")
print("NOT PROVED: independent precipitation validity, frost risk, C3d ET0 parity, botanical accuracy.")
