import argparse
import json
from pathlib import Path
from .sources import WorldClim
from .worker import run,verify_manifest

def main():
    p=argparse.ArgumentParser(description='Public, botanically agnostic climate collection worker')
    sub=p.add_subparsers(dest='cmd',required=True)
    r=sub.add_parser('run')
    r.add_argument('--plan',type=Path,default=Path('config/plan.json'))
    r.add_argument('--output',type=Path,default=Path('published'))
    r.add_argument('--cache',type=Path,default=Path('.climate-cache'))
    r.add_argument('--max-tiles',type=int,default=1)
    v=sub.add_parser('verify');v.add_argument('--output',type=Path,default=Path('published'))
    args=p.parse_args()
    if args.cmd=='verify':print(json.dumps({'verified_tiles':verify_manifest(args.output)}));return
    if args.max_tiles<=0:raise SystemExit('max-tiles must be positive')
    plan=json.loads(args.plan.read_text())['tiles']
    manifest_path=args.output/'manifest.json'
    done=json.loads(manifest_path.read_text()).get('tiles',{}) if manifest_path.exists() else {}
    if all(x['id'] in done for x in plan):
        print(json.dumps({'new_tiles':0,'message':'all planned tiles complete'}));return
    src=WorldClim(args.cache)
    count=run(args.plan,args.output,src,args.max_tiles)
    print(json.dumps({'new_tiles':count,'provider':src.name,'baseline':src.baseline}))
if __name__=='__main__':main()
