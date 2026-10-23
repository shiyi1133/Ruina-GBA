"""Compare the original native map art with the released v0.5.1 palette.

This is an asset census, not evidence of a new renderer or emulator output.
All comparisons discard only the RGB bits GBA hardware cannot represent.
"""
import hashlib,json,struct,zipfile,zlib
from pathlib import Path
import numpy as np
from PIL import Image
from project_env import ROOT,ARCHIVE
from native_music_assets import logical,hash_name

def main():
 manifest=json.loads((ROOT/'history/quality_performance_20261022/baseline/build/asset_manifest.json').read_text())
 resources={(r['kind'],r['hash']):r['image']for r in manifest['resources']}
 rows=[]
 with zipfile.ZipFile(ARCHIVE)as z:
  for original in z.namelist():
   path=logical(original);parts=path.split('/')
   if len(parts)<2 or parts[-2]not in('Panorama','ChipSet','CharSet')or not path.endswith('.xyz'):continue
   kind={'Panorama':1,'ChipSet':2,'CharSet':3}[parts[-2]];idx=resources[kind,hash_name(Path(path).stem)]
   raw=z.read(original);w,h=struct.unpack_from('<HH',raw,4);d=zlib.decompress(raw[8:]);palette=np.frombuffer(d[:768],np.uint8).reshape(256,3)
   indices=np.frombuffer(d[768:],np.uint8).reshape(h,w);rgb=palette[indices]>>3
   label=manifest['images'][idx];old=np.asarray(Image.open(ROOT/'history/quality_performance_20261022/baseline/art'/(label+'_palette.png')).convert('RGB'))>>3
   assert old.shape==rgb.shape,(path,old.shape,rgb.shape)
   mask=indices!=0 if kind in(2,3)else np.ones((h,w),bool)
   a=rgb[mask].astype(np.int16);b=old[mask].astype(np.int16)
   rows.append({'source':path,'image_id':idx,'label':label,'kind':kind,'width':w,'height':h,'visible_pixels':int(mask.sum()),
                'original_RGB555_colors':len(np.unique(a,axis=0)),'released_visible_colors':len(np.unique(b,axis=0)),
                'released_different_pixels':int(np.any(a!=b,axis=1).sum()),'released_RGB555_MAE':float(np.abs(a-b).mean()),
                'source_sha256':hashlib.sha256(raw).hexdigest()})
 out=ROOT/'evidence/optimization_20261022/art';out.mkdir(parents=True,exist_ok=True)
 report={'kind':'original asset comparison at GBA RGB555 precision; not a gameplay screenshot','baseline':'v0.5.1',
         'resources':rows,'pixels':sum(r['visible_pixels']for r in rows),
         'different_pixels':sum(r['released_different_pixels']for r in rows)}
 (out/'original_census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in report.items()if k!='resources'},ensure_ascii=False,indent=2))
 print(json.dumps(sorted(rows,key=lambda r:-r['released_RGB555_MAE'])[:8],ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
