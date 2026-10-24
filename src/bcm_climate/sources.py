"""Provider-neutral sampler interface and WorldClim 2.1 bootstrap implementation.

WorldClim 2.1's 1970-2000 monthly normals are NOT C3d's 1991-2020
reference, nor are monthly tmin/tmax averages historical cold extremes.
"""
import hashlib
import json
import os
from pathlib import Path
from urllib.request import urlopen, Request
from zipfile import ZipFile
from shapely.geometry import Point, shape
from shapely.ops import unary_union
from shapely.prepared import prep
import rasterio
import numpy as np

WORLDCLIM_BASE = "https://geodata.ucdavis.edu/climate/worldclim/2_1/base"
LAND_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_land.geojson"
VARIABLES = ("tavg", "tmin", "tmax", "prec")


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def download_once(url: str, dest: Path, max_bytes: int=150_000_000) -> Path:
    """Atomic cached download; bounded size and no partial replacement."""
    if dest.exists(): return dest
    dest.parent.mkdir(parents=True,exist_ok=True)
    tmp=dest.with_suffix(dest.suffix+'.partial')
    try:
        req=Request(url,headers={'User-Agent':'botanical-climate-data/0.1 (+research)'})
        n=0
        with urlopen(req, timeout=90) as src, open(tmp,'wb') as out:
            while True:
                block=src.read(1_048_576)
                if not block: break
                n+=len(block)
                if n>max_bytes: raise ValueError(f"Download over budget ({max_bytes} bytes): {url}")
                out.write(block)
        if n == 0: raise ValueError('Empty provider download')
        os.replace(tmp,dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest

class LandMask:
    """Coarse Natural Earth land centre mask: coastlines are approximate."""
    def __init__(self, path:Path):
        data=json.loads(path.read_text())
        polys=[shape(f['geometry']) for f in data['features'] if f.get('geometry')]
        self.geom=prep(unary_union(polys))
        self.hash=sha256(path)
    def covers(self, lon:float, lat:float)->bool:
        return self.geom.covers(Point(lon,lat))

class WorldClim:
    """Samples 12 monthly GeoTIFFs per variable directly from ZIP archives."""
    baseline='1970-2000'
    name='worldclim-2.1-10m'
    def __init__(self, cache:Path):
        self.cache=Path(cache);self.paths={}
        for var in VARIABLES:
            fn=f'wc2.1_10m_{var}.zip'
            self.paths[var]=download_once(f'{WORLDCLIM_BASE}/{fn}',self.cache/fn)
        land=download_once(LAND_URL,self.cache/'ne_110m_land.geojson',max_bytes=2_000_000)
        self.land=LandMask(land)
        self.hashes={var:sha256(p) for var,p in self.paths.items()}
        self.hashes['landmask']=self.land.hash
    def land_covers(self, lon,lat): return self.land.covers(lon,lat)
    def sample(self,cells):
        """Return each cell's 48-element profile or None if source has missing pixels."""
        coords=[(c.lon,c.lat) for c in cells]
        profiles={c.id: {} for c in cells}
        for var in VARIABLES:
            p=self.paths[var]
            with ZipFile(p) as archive:
                names=[x for x in archive.namelist() if x.lower().endswith('.tif')]
                month_names={}
                for name in names:
                    suffix=name.rsplit('_',1)[-1].split('.')[0]
                    if suffix.isdigit() and int(suffix) in range(1,13):
                        month_names[int(suffix)]=name
                if len(month_names)!=12: raise ValueError(f'Expected 12 monthly TIFFs in {p}; found {len(month_names)}')
                for m in range(1,13):
                    vpath=f'/vsizip/{p.resolve().as_posix()}/{month_names[m]}'
                    with rasterio.open(vpath) as ds:
                        values=list(ds.sample(coords,masked=True))
                        scale=(ds.scales[0] if ds.scales else 1) or 1
                        offset=ds.offsets[0] if ds.offsets else 0
                        for c,value in zip(cells,values):
                            raw=value[0]
                            v=None if np.ma.is_masked(raw) or not np.isfinite(raw) else float(raw*scale+offset)
                            profiles[c.id].setdefault(var,[]).append(v)
        # Fail-closed units sanity check: no guessed /10 correction.
        for c in cells:
            d=profiles[c.id]
            if any(v is None for vals in d.values() for v in vals):
                profiles[c.id]=None; continue
            if any(not (-100<=v<=80) for v in d['tavg']+d['tmin']+d['tmax']):
                raise ValueError(f'Unsafe temperature units / scaling for {c.id}; examine GeoTIFF scales')
            if any(v<0 or v>5000 for v in d['prec']):
                raise ValueError(f'Unsafe precipitation units for {c.id}')
            if any(lo>mean+.75 or mean>hi+.75 for lo,mean,hi in zip(d['tmin'],d['tavg'],d['tmax'])):
                raise ValueError(f'Inconsistent temperature means for {c.id}')
        return profiles
