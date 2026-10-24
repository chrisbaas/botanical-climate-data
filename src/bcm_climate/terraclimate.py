"""Source adapter: 1991-2020 TerraClimate monthly normals, not C3d daily weather."""
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
from .sources import download_once,sha256,LandMask,LAND_URL
BASE="https://thredds.northwestknowledge.net/thredds/fileServer/TERRACLIMATE_ALL/climatology"
VARIABLES=("tmin","tmax","ppt","pet")
class TerraClimateNormals:
    name="terraclimate-19912020-climatology"
    baseline="1991-2020"
    def __init__(self,cache):
        cache=Path(cache);self.paths={}
        for var in VARIABLES:
            filename=f"TerraClimate_19912020_{var}.nc"
            self.paths[var]=download_once(f"{BASE}/{filename}",cache/filename,max_bytes=160_000_000)
        land=download_once(LAND_URL,cache/"ne_110m_land.geojson",max_bytes=2_000_000)
        self.land=LandMask(land)
        self.hashes={var:sha256(path) for var,path in self.paths.items()}
        self.hashes["landmask"]=self.land.hash
    def land_covers(self,lon,lat):
        return self.land.covers(lon,lat)
    def sample(self,cells):
        result={c.id:{} for c in cells}
        if not cells:return result
        prior_lat=prior_lon=None
        for var,path in self.paths.items():
            with Dataset(path) as ds:
                lat=np.asarray(ds.variables["lat"][:],dtype=float)
                lon=np.asarray(ds.variables["lon"][:],dtype=float)
                if prior_lat is None:prior_lat,prior_lon=lat,lon
                elif not np.array_equal(lat,prior_lat) or not np.array_equal(lon,prior_lon):
                    raise ValueError("Native source grids do not match")
                v=ds.variables[var]
                if len(v.shape)!=3 or v.shape[0]!=12 or v.shape[1:]!=(len(lat),len(lon)):
                    raise ValueError(f"Invalid 12-month climatology: {var}: {v.shape}")
                row=[int(np.argmin(abs(lat-c.lat))) for c in cells]
                col=[int(np.argmin(abs(lon-c.lon))) for c in cells]
                lo,hi=min(row),max(row)+1
                left,right=min(col),max(col)+1
                # Read only the local rectangle from the cached global NetCDF.
                block=v[:,lo:hi,left:right]
                for c,r,j in zip(cells,row,col):
                    val=block[:,r-lo,j-left]
                    if np.ma.getmaskarray(val).any():result[c.id][var]=None
                    else:
                        a=np.asarray(val,dtype=float)
                        result[c.id][var]=a.tolist() if np.all(np.isfinite(a)) else None
        for c in cells:
            x=result[c.id]
            if any(x[v] is None for v in VARIABLES):result[c.id]=None;continue
            if any(y<-100 or y>80 for v in ("tmin","tmax") for y in x[v]):
                raise ValueError(f"Invalid temperature or units: {c.id}")
            if any(a>b+.75 for a,b in zip(x["tmin"],x["tmax"])):
                raise ValueError(f"Invalid min/max relation: {c.id}")
            if any(y<0 or y>6000 for v in ("ppt","pet") for y in x[v]):
                raise ValueError(f"Invalid moisture variable: {c.id}")
            if sum(x["pet"])<=0:raise ValueError(f"Invalid annual reference ET: {c.id}")
        return result
