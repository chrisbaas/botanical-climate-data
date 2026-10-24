import json
import numpy as np
import pytest
from netCDF4 import Dataset
from bcm_climate.terraclimate import validate_metadata
from bcm_climate.worker_19912020 import run

def fixture_file(path):
    with Dataset(path,'w') as ds:
        for name,n in [('time',12),('lat',4320),('lon',8640)]:ds.createDimension(name,n)
        ds.createVariable('time','f8',('time',))[:]=np.arange(1,13)
        ds.createVariable('lat','f8',('lat',))[:]=90-(np.arange(4320)+.5)/24
        ds.createVariable('lon','f8',('lon',))[:]=-180+(np.arange(8640)+.5)/24
        v=ds.createVariable('tmin','i2',('time','lat','lon'),zlib=True)
        v.units='deg C';v.scale_factor=.1;v.add_offset=-73.

@pytest.mark.parametrize('fault',['units','scale','offset','months','coordinates'])
def test_metadata_fail_closed(tmp_path,fault):
    p=tmp_path/'test.nc';fixture_file(p)
    with Dataset(p,'a') as d:
        validate_metadata(d,'tmin')
        if fault=='units':d.variables['tmin'].units='K'
        if fault=='scale':d.variables['tmin'].scale_factor=1.
        if fault=='offset':d.variables['tmin'].add_offset=0.
        if fault=='months':d.variables['time'][:]=np.arange(12)
        if fault=='coordinates':d.variables['lat'][0]=0
        with pytest.raises(ValueError):validate_metadata(d,'tmin')

@pytest.mark.parametrize('n',[0,-1,4])
def test_job_limit(tmp_path,n):
    with pytest.raises(ValueError,match='limit'):run(tmp_path/'absent',tmp_path/'out',None,n)
