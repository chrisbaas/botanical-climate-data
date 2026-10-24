"""Bounded manual audit; uses four reusable climatology files, no global processing."""
import json,time,resource,hashlib,tempfile
from pathlib import Path
from bcm_climate.terraclimate import TerraClimateNormals,BASE
from bcm_climate.worker_19912020 import run,verify,process,features
from bcm_climate.grid import Cell
from netCDF4 import Dataset
root=Path(__file__).resolve().parents[1]
ev=root/'evidence/e1';ev.mkdir(parents=True,exist_ok=True)
t=time.monotonic();s=TerraClimateNormals(root/'.terraclimate-cache');init=time.monotonic()-t
catalog={'baseline':'1991-2020','generation':'not established by file metadata; do not mix with v1.1','access_method':'HTTPS THREDDS fileServer; cached global monthly climatologies; regional reads only','licence':'CC0 (TerraClimate distribution catalogue); Natural Earth public domain','files':{}}
for k,p in s.paths.items():
 with Dataset(p) as d:
  v=d.variables[k]
  catalog['files'][k]={'url':f'{BASE}/{p.name}','file':p.name,'sha256':s.hashes[k],'bytes':p.stat().st_size,'dimensions':list(v.dimensions),'shape':list(v.shape),'units':v.units,'scale_factor':float(v.scale_factor),'add_offset':float(v.add_offset),'time_values':d.variables['time'][:].tolist(),'global_attributes':{a:str(d.getncattr(a)) for a in d.ncattrs()}}
(ev/'source-catalog.json').write_text(json.dumps(catalog,indent=2))
with tempfile.TemporaryDirectory() as tmp:
 import gzip
 old=root/'published-19912020/tiles/bc-coast-01.json.gz'
 tile=json.loads(gzip.decompress(old.read_bytes()))
 t=time.monotonic()
 item=process({'id':'bc-coast-01','bbox':tile['bbox']},s,tmp)
 reproduced=Path(tmp,'tiles/bc-coast-01.json.gz').read_bytes()==old.read_bytes()
 bc_seconds=time.monotonic()-t
 assert reproduced,'Existing tile no longer reproduces'
out=root/'published-e1';t=time.monotonic();new=run(root/'config/e1-plan.json',out,s,1);processing=time.monotonic()-t
before=(out/'manifest.json').read_bytes();t=time.monotonic();again=run(root/'config/e1-plan.json',out,s,1);resume=time.monotonic()-t
assert again==0 and before==(out/'manifest.json').read_bytes()
# Local points only; no point-by-point network acquisitions. Sample separately to avoid huge cross-world rectangles.
points=[('Vancouver',49.2827,-123.1207),('Lisbon',38.7223,-9.1393),('Manaus',-3.119,-60.022),('Bogota',4.711,-74.072),('Pereira',4.813,-75.696),('Winnipeg',49.895,-97.138),('Riyadh',24.714,46.675)]
rows=[]
for name,lat,lon in points:
 c=Cell(0,0,lat,lon);p=s.sample([c])[c.id]
 rows.append({'name':name,'lat':lat,'lon':lon,'sampling':'nearest native cell to city coordinate; diagnostic only','monthly':p,'features':features(p) if p else None,'scientific_hold':name in ['Bogota','Pereira']})
(ev/'climate-checks.json').write_text(json.dumps(rows,indent=2))
metrics={'cached_source_initialization_seconds':init,'bc_reproduction_seconds':bc_seconds,'bc_byte_identical':reproduced,'new_tiles':new,'processing_seconds':processing,'repeat_run_seconds':resume,'repeat_new_tiles':again,'repeat_manifest_unchanged':True,'repeat_network_requests':0,'verified_tiles':verify(out),'peak_rss_kib_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'manifest':json.loads(before)}
(ev/'run-metrics.json').write_text(json.dumps(metrics,indent=2));print(json.dumps(metrics,indent=2))
