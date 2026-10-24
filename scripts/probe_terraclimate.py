"""Bounded TerraClimate 1991-2020 and current data access diagnostics."""
from urllib.request import Request, urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError

host="https://thredds.northwestknowledge.net"
bbox=dict(var="tmin",west="-123.5",east="-123.0",south="49.0",north="49.5",accept="netcdf",addLatLon="true")
urls=[
 ("normal ncss",f"{host}/thredds/ncss/TERRACLIMATE_ALL/climatology/TerraClimate_19912020_tmin.nc?"+urlencode(bbox),"GET"),
 ("normal dods metadata",f"{host}/thredds/dodsC/TERRACLIMATE_ALL/climatology/TerraClimate_19912020_tmin.nc.dds","GET"),
 ("normal fileserver",f"{host}/thredds/fileServer/TERRACLIMATE_ALL/climatology/TerraClimate_19912020_tmin.nc","HEAD"),
 ("current aggregate ncss",f"{host}/thredds/ncss/agg_terraclimate_tmin_1950_CurrentYear_GLOBE.nc?"+urlencode({**bbox,"time_start":"2020-01-01T00:00:00Z","time_end":"2020-12-31T00:00:00Z"}),"GET"),
 ("2020 ncss",f"{host}/thredds/ncss/TERRACLIMATE_ALL/data/TerraClimate_tmin_2020.nc?"+urlencode(bbox),"GET"),
 ("2020 fileserver",f"{host}/thredds/fileServer/TERRACLIMATE_ALL/data/TerraClimate_tmin_2020.nc","HEAD")
]
for label,url,method in urls:
 print("Checking",label,url,flush=True)
 try:
  req=Request(url,method=method,headers={"User-Agent":"BCM-public-collector/0.2"})
  with urlopen(req,timeout=16) as resp:
   b=resp.read(1024) if method=="GET" else b''
   print("HTTP",resp.status,"content-type",resp.headers.get("Content-Type"),"content-length",resp.headers.get("Content-Length"),"sample-bytes",len(b),"magic",b[:24].hex(),flush=True)
 except Exception as exc:
  print("ERROR",type(exc).__name__,str(exc)[:250],flush=True)
