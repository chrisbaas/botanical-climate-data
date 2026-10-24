import argparse,json
from pathlib import Path
from .worker_19912020 import run,verify
from .terraclimate import TerraClimateNormals
def main():
    p=argparse.ArgumentParser(description="1991–2020 monthly source; never claim exact C3d output")
    sub=p.add_subparsers(dest="command",required=True)
    x=sub.add_parser("run")
    x.add_argument("--max-tiles",type=int,default=1)
    x.add_argument("--plan",type=Path,default=Path("config/plan.json"))
    x.add_argument("--output",type=Path,default=Path("published-19912020"))
    x.add_argument("--cache",type=Path,default=Path(".terraclimate-cache"))
    y=sub.add_parser("verify")
    y.add_argument("--output",type=Path,default=Path("published-19912020"))
    a=p.parse_args()
    if a.command=="verify":
        print(json.dumps({"verified_tiles":verify(a.output)}));return
    if not 1 <= a.max_tiles <= 3:raise SystemExit("Pilot limit is 1 to 3 tiles")
    plan=json.loads(a.plan.read_text())["tiles"]
    mf=a.output/"manifest.json"
    done=json.loads(mf.read_text()).get("tiles",{}) if mf.exists() else {}
    if mf.exists(): verify(a.output)
    if all(t["id"] in done for t in plan):
        print(json.dumps({"new_tiles":0,"message":"Pilot complete"}));return
    src=TerraClimateNormals(a.cache)
    print(json.dumps({"new_tiles":run(a.plan,a.output,src,a.max_tiles),
                      "source":src.name,"baseline":src.baseline}))
if __name__=="__main__":main()
