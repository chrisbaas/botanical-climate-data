"""Offline acceptance tests for independent 1991–2020 monthly profile outputs."""
import gzip,json
import pytest
from bcm_climate.worker_19912020 import run,verify,features
class Dummy:
    name="dummy"
    baseline="1991-2020"
    hashes={"tmin":"A","tmax":"B","ppt":"C","pet":"D","landmask":"E"}
    def land_covers(self,lon,lat):return lon<0
    def sample(self,cells):
        return {c.id:{"tmin":[3.]*12,"tmax":[15.]*12,"ppt":[50.]*12,"pet":[25.]*12} for c in cells}
def test_features():
    f=features({"tmin":[3.]*12,"tmax":[15.]*12,"ppt":[50.]*12,"pet":[25.]*12})
    assert f["annual_mean_temperature_estimate_c"]==9
    assert f["p_over_terraclimate_reference_et"]==2
    assert f["annual_absolute_minimum_c"] is None
def test_resumable_schema(tmp_path):
    p=tmp_path/"plan.json"
    p.write_text(json.dumps({"tiles":[{"id":"demo","bbox":[-.5,0,.5,.25]}]}))
    out=tmp_path/"new"
    assert run(p,out,Dummy())==1
    assert verify(out)==1
    m=json.loads((out/"manifest.json").read_text())
    assert m["schema"]=="bcm-climate-monthly-v0.2"
    obj=json.loads(gzip.decompress((out/"tiles/demo.json.gz").read_bytes()))
    assert obj["coverage"]["land_centres"]==2
    assert "no_frost_extremes" in obj["cells"][0]["quality_flags"]
    assert run(p,out,Dummy())==0
    broken=Dummy();broken.hashes=dict(broken.hashes);broken.hashes["pet"]="changed"
    with pytest.raises(ValueError):run(p,out,broken)
    (out/"tiles/demo.json.gz").write_bytes(b"corrupt")
    with pytest.raises(ValueError):verify(out)
