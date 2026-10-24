"""Exercise the real raster ZIP reader with tiny generated GeoTIFFs, not just a mock source."""
import json
import zipfile
from pathlib import Path
import numpy as np
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from bcm_climate.sources import WorldClim,VARIABLES
from bcm_climate.grid import cells_for_bbox


def test_worldclim_zip_sampler(tmp_path, monkeypatch):
    # One valid west cell; eastern sample intentionally marked nodata.
    geo={"type":"FeatureCollection","features":[{"type":"Feature","properties":{},
      "geometry":{"type":"Polygon","coordinates":[[[-1,-1],[1,-1],[1,1],[-1,1],[-1,-1]]]}}]}
    (tmp_path/'land.geojson').write_text(json.dumps(geo))
    for var in VARIABLES:
        file=tmp_path/f'wc2.1_10m_{var}.zip'
        with zipfile.ZipFile(file,'w') as z:
            for month in range(1,13):
                pixels=np.array([[20.,-9999.]], dtype='float32')
                if var=='tmin':pixels[0,0]=15
                if var=='tmax':pixels[0,0]=25
                if var=='prec':pixels[0,0]=50
                with MemoryFile() as m:
                    with m.open(driver='GTiff',height=1,width=2,count=1,dtype='float32',
                                transform=from_origin(-.5,.25,.25,.25),crs='EPSG:4326',nodata=-9999) as d:
                        d.write(pixels,1)
                    z.writestr(f'wc2.1_10m_{var}_{month:02d}.tif',m.read())
    def fake_download(url,dest,max_bytes=150_000_000):
        source=tmp_path/('land.geojson' if str(dest).endswith('.geojson') else dest.name)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(source.read_bytes())
        return dest
    monkeypatch.setattr('bcm_climate.sources.download_once',fake_download)
    src=WorldClim(tmp_path/'cache')
    c=list(cells_for_bbox(-.5,0,0,.25))
    profiles=src.sample(c)
    assert len(profiles)==2
    assert profiles[c[0].id]['tavg']==[20.]*12
    assert profiles[c[0].id]['prec']==[50.]*12
    assert profiles[c[1].id] is None
