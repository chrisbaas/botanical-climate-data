"""Incremental immutable climate-tile publication with a verifiable manifest."""
import gzip
import hashlib
import json
import os
from pathlib import Path
from .grid import cells_for_bbox
from .features import summarise

SCHEMA='bcm-climate-monthly-v0.1'

def bjson(obj):
    return (json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode('utf8')

def atomic(path:Path, data:bytes):
    path.parent.mkdir(parents=True,exist_ok=True)
    p=path.with_suffix(path.suffix+'.tmp')
    try:
        p.write_bytes(data);os.replace(p,path)
    finally:p.unlink(missing_ok=True)

def gzip_deterministic(data:bytes)->bytes:
    return gzip.compress(data,compresslevel=9,mtime=0)

def process_tile(spec, source, output_dir:Path):
    output_dir=Path(output_dir);id=spec['id'];bounds=spec['bbox']
    candidates=list(cells_for_bbox(*bounds))
    land=[c for c in candidates if source.land_covers(c.lon,c.lat)]
    profiles=source.sample(land) if land else {}
    rows=[];missing=0
    for c in land:
        profile=profiles[c.id]
        if profile is None:
            missing+=1
            rows.append({'cell_id':c.id,'lat':c.lat,'lon':c.lon,'status':'source_missing',
                         'monthly':None,'features':None,'quality_flags':['monthly_nodata']})
            continue
        rows.append({'cell_id':c.id,'lat':c.lat,'lon':c.lon,'status':'monthly_profile',
                     'monthly':{'temperature_mean_c':profile['tavg'],
                                'temperature_min_daily_mean_c':profile['tmin'],
                                'temperature_max_daily_mean_c':profile['tmax'],
                                'precipitation_total_mm':profile['prec']},
                     'features':summarise(profile),
                     'quality_flags':['monthly_normals_only','no_daily_extremes','no_frost_reliability',
                                      'no_reference_et0','approximate_coastal_land_mask']})
    payload={'schema':SCHEMA,'tile_id':id,'grid_degrees':0.25,'bbox':bounds,
             'source':{'name':source.name,'baseline':source.baseline,'file_sha256':source.hashes},
             'limitations':['Not exact C3d inputs or classifications',
                            'Climate source period and resolution are not the C3d reference',
                            'Land-mask is cartographically coarse'],
             'coverage':{'grid_positions':len(candidates),'land_centres':len(land),
                         'ocean_centres':len(candidates)-len(land),'missing_land_profiles':missing},
             'cells':rows}
    raw=bjson(payload);packed=gzip_deterministic(raw)
    tile_file=output_dir/'tiles'/f'{id}.json.gz'
    if tile_file.exists():
        if tile_file.read_bytes()!=packed:raise ValueError(f'Tile already exists with different content: {id}; never overwrite')
    else:atomic(tile_file,packed)
    return {'file':f'tiles/{id}.json.gz','sha256':hashlib.sha256(packed).hexdigest(),
            'bytes':len(packed),'coverage':payload['coverage'],
            'source':payload['source']}

def verify_manifest(output_dir:Path):
    path=Path(output_dir)/'manifest.json';data=json.loads(path.read_text())
    for key,item in data['tiles'].items():
        p=Path(output_dir)/item['file']
        if hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:
            raise ValueError(f'Invalid checksum: {key}')
        raw=json.loads(gzip.decompress(p.read_bytes()))
        if raw['tile_id']!=key or raw['schema']!=SCHEMA:raise ValueError(f'Tile schema mismatch: {key}')
    return len(data['tiles'])

def run(plan_path:Path, output_dir:Path, source, max_tiles:int=1):
    plan=json.loads(Path(plan_path).read_text())['tiles']
    out=Path(output_dir);out.mkdir(parents=True,exist_ok=True)
    manifest_path=out/'manifest.json'
    if manifest_path.exists(): manifest=json.loads(manifest_path.read_text())
    else: manifest={'schema':SCHEMA,'tiles':{}}
    # Fail closed if a future provider download changes beneath an existing dataset.
    for previous in manifest['tiles'].values():
        current={'name':source.name,'baseline':source.baseline,'file_sha256':source.hashes}
        if previous['source'] != current:
            raise ValueError('Provider source drift: start a new versioned dataset; do not combine differing inputs')
    n=0
    for spec in plan:
        if spec['id'] in manifest['tiles']:continue
        item=process_tile(spec,source,out)
        manifest['tiles'][spec['id']]=item
        atomic(manifest_path,bjson(manifest)) # completed tile becomes durable immediately
        n+=1
        if n>=max_tiles:break
    verify_manifest(out)
    return n
