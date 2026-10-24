"""Source adapter: 1991-2020 TerraClimate monthly normals, not C3d daily weather."""
from pathlib import Path
import numpy as np
from netCDF4 import Dataset
from .sources import download_once,sha256,LandMask,LAND_URL
BASE="https://thredds.northwestknowledge.net/thredds/fileServer/TERRACLIMATE_ALL/climatology"
VARIABLES=("tmin","tmax","ppt","pet")
# Audited file identities; updating these requires a new reviewed source version.
EXPECTED_HASHES={'landmask': '9e0729ee253ca7d7a5c4ae9395fb1902264c5377c52e224d13dd85010e2835d9', 'pet': '9db4b1dde786731be0f40f359115518099d5f0dcb464a205132a51ca290b694a', 'ppt': 'eae7eaa3f27c17376178af7a51e6cc5918287d99df35dc00e93ef274b174f211', 'tmax': '04e1293284826d5c9814336a52c389d8552523dbe3ccd3aca072e6ca17ac6f58', 'tmin': '93961a5e423c02282bc1aea2761dbdd28bb8ec1ee79ca571f4b8b1db29d42a7a'}

def validate_metadata(ds, var):
    """Reject changed dimensions, units, packing, or month order before sampling."""
    v=ds.variables[var]
    expected_units="deg C" if var in ("tmin","tmax") else "mm"
    if v.dimensions != ("time","lat","lon") or v.shape != (12,4320,8640):
        raise ValueError("Unexpected source dimensions")
    if getattr(v,"units",None) != expected_units:
        raise ValueError("Unexpected source units")
    if not np.isclose(getattr(v,"scale_factor",float("nan")),.1):
        raise ValueError("Unexpected source scale")
    offset=-73.0 if var in ("tmin","tmax") else 0.0
    if not np.isclose(getattr(v,"add_offset",float("nan")),offset):
        raise ValueError("Unexpected source offset")
    if not np.array_equal(ds.variables["time"][:],np.arange(1,13)):
        raise ValueError("Unexpected month order")
    for key,expected in (("lat",90-(np.arange(4320)+.5)/24),("lon",-180+(np.arange(8640)+.5)/24)):
        if not np.allclose(ds.variables[key][:],expected,rtol=0,atol=1e-8):
            raise ValueError("Unexpected source coordinates")

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
        if self.hashes != EXPECTED_HASHES:
            raise ValueError("Source file identity changed; retain cache and review a new source version")
        for var,path in self.paths.items():
            with Dataset(path) as ds: validate_metadata(ds,var)
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
