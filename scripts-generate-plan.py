"""One-time OPTIONAL deterministic global 5-degree plan generator.

Do not replace the three-tile pilot plan until source and costs are validated.
"""
import argparse,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
a=p.parse_args()
tiles=[]
for south in range(-90,90,5):
 for west in range(-180,180,5):
  tiles.append({'id':f'global_{south+90:03d}_{west+180:03d}',
                'bbox':[west,south,west+5,south+5]})
a.output.write_text(json.dumps({'description':'GLOBAL PLAN: explicit opt-in only',
                                 'tiles':tiles},indent=2)+'\n')
print(len(tiles),'global 5-degree tiles (including wholly marine windows)')
