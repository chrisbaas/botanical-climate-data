import gzip,json
from pathlib import Path
import pytest
from bcm_climate.grid import cells_for_bbox
from bcm_climate.worker import run,verify_manifest

class TinySource:
    name='fixture-only';baseline='test-2000'
    hashes={'temperature':'abc','landmask':'def'}
    def land_covers(self,lon,lat):return lon<0
    def sample(self,cells):
        return {c.id:{'tavg':[10.0]*12,'tmin':[5.0]*12,'tmax':[15.0]*12,'prec':[50.0]*12}
                for c in cells}

def test_grid_ids_stable():
    cells=list(cells_for_bbox(-0.5,0,0.5,0.25))
    assert len(cells)==4
    assert [c.id for c in cells]==['g025_r0360_c0718','g025_r0360_c0719','g025_r0360_c0720','g025_r0360_c0721']

def test_misaligned_bbox_rejected():
    with pytest.raises(ValueError):list(cells_for_bbox(-.51,0,1,1))

def test_incremental_and_integrity(tmp_path):
    plan=tmp_path/'plan.json';out=tmp_path/'published'
    plan.write_text(json.dumps({'tiles':[{'id':'first','bbox':[-.5,0,.5,.25]},
                                         {'id':'second','bbox':[-.5,.25,.5,.5]}]}))
    assert run(plan,out,TinySource(),1)==1
    assert verify_manifest(out)==1
    tile=json.loads(gzip.decompress((out/'tiles/first.json.gz').read_bytes()))
    assert tile['coverage']=={'grid_positions':4,'land_centres':2,'ocean_centres':2,'missing_land_profiles':0}
    assert tile['cells'][0]['features']['annual_precipitation_mm']==600
    assert all(x['features']['winter_absolute_minimum_c'] is None for x in tile['cells'])
    original=(out/'tiles/first.json.gz').read_bytes()
    assert run(plan,out,TinySource(),1)==1
    assert run(plan,out,TinySource(),1)==0
    assert verify_manifest(out)==2
    assert (out/'tiles/first.json.gz').read_bytes()==original
    (out/'tiles/first.json.gz').write_bytes(b'invalid')
    with pytest.raises(ValueError):verify_manifest(out)

def test_fail_closed_no_plant_classification(tmp_path):
    plan=tmp_path/'p.json';plan.write_text(json.dumps({'tiles':[{'id':'a','bbox':[-.25,0,.25,.25]}]}))
    out=tmp_path/'out';run(plan,out,TinySource(),1)
    payload=json.loads(gzip.decompress((out/'tiles/a.json.gz').read_bytes()))
    assert all('plant' not in str(k).lower() for c in payload['cells'] for k in c.keys())
