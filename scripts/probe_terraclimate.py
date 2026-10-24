"""Bounded (<=8 MB) public TerraClimate 1991-2020 NCSS connectivity/provenance probe.

This does not publish or classify anything. Errors are explicit.
"""
import tempfile
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from netCDF4 import Dataset

HOST="https://thredds.northwestknowledge.net"
PATH="/thredds/ncss/TERRACLIMATE_ALL/climatology/TerraClimate_19912020_tmin.nc"
params={"var":"tmin","west":"-123.5","east":"-123.0","south":"49.0",
        "north":"49.5","accept":"netcdf","addLatLon":"true"}
url=HOST+PATH+"?"+urlencode(params)
print("Request",url,flush=True)
with urlopen(Request(url,headers={"User-Agent":"botanical-climate-data/0.2 climate science test"}),timeout=75) as stream:
    print("HTTP",stream.status,"type",stream.headers.get("Content-Type"),flush=True)
    data=stream.read(8_000_001)
if len(data)>8_000_000:raise SystemExit("Safety cap >8 MB")
print("Response bytes",len(data),flush=True)
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/"probe.nc";path.write_bytes(data)
    with Dataset(path) as ds:
        print("Dimensions",[(k,len(v)) for k,v in ds.dimensions.items()],flush=True)
        print("Variables",[(k,str(v.shape),getattr(v,'units','')) for k,v in ds.variables.items()],flush=True)
        if 'tmin' not in ds.variables:raise ValueError("Expected tmin missing")
        values=ds.variables['tmin'][:]
        print("Range",float(values.min()),float(values.max()),"masks",sum(values.mask.flat) if hasattr(values,'mask') and hasattr(values.mask,'flat') else 'scalar',flush=True)
        if values.size < 12:raise ValueError("Missing 12 monthly samples")
print("1991-2020 NCSS probe passed",flush=True)
