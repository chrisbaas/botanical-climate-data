"""Audit one 1991-2020 TerraClimate climatology variable (no publication)."""
from pathlib import Path
from urllib.request import Request,urlopen
from netCDF4 import Dataset
import hashlib,os

url="https://thredds.northwestknowledge.net/thredds/fileServer/TERRACLIMATE_ALL/climatology/TerraClimate_19912020_tmin.nc"
out=Path("/tmp/bcm-terraclimate-19912020-tmin.nc")
limit=115_000_000
digest=hashlib.sha256();total=0
with urlopen(Request(url,headers={"User-Agent":"BCM-public-collector/0.2"}),timeout=90) as resp:
 print("HTTP",resp.status,"content-length",resp.headers.get("Content-Length"),flush=True)
 with out.open('wb') as f:
  for block in iter(lambda:resp.read(1024*1024),b''):
   total+=len(block)
   if total>limit:raise ValueError("Source exceeds bounded file cap")
   digest.update(block);f.write(block)
print("Downloaded",total,"bytes SHA256",digest.hexdigest(),flush=True)
with Dataset(out) as ds:
 print("Global attributes",{k:str(getattr(ds,k))[:180] for k in ds.ncattrs() if k.lower() in ('title','history','source','version','time_coverage_start','time_coverage_end')},flush=True)
 print("Dims",[(k,len(v)) for k,v in ds.dimensions.items()],flush=True)
 print("Variables",[(k,str(v.shape),str(getattr(v,'units',''))) for k,v in ds.variables.items()],flush=True)
 if 'tmin' not in ds.variables:raise ValueError('Missing tmin')
 import numpy as np
 lats=ds.variables['lat'][:];lons=ds.variables['lon'][:];v=ds.variables['tmin']
 for label,lat,lon in [('Vancouver',49.25,-123.12),('Lisbon',38.72,-9.14),('Bogota',4.71,-74.07),('Winnipeg',49.9,-97.14)]:
  i=int(np.argmin(abs(lats-lat)));j=int(np.argmin(abs(lons-lon)))
  ar=v[:,i,j]
  print(label,'coords',float(lats[i]),float(lons[j]),'monthly raw',ar.tolist(),
        'minmax',float(ar.min()),float(ar.max()),flush=True)
  if ar.size!=12 or np.ma.getmaskarray(ar).any():raise ValueError('Invalid source data')
  if not np.all(np.isfinite(ar)) or np.min(ar)<-100 or np.max(ar)>60:raise ValueError('Unexpected temperature units')
print('OK: full 1991-2020 file validated for one variable',flush=True)
