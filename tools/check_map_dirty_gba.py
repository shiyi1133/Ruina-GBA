"""Pixel equivalence of cached region redraws vs complete scene redraws."""
import hashlib,json
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture

def main():
 out=ROOT/'evidence/performance/map_dirty';out.mkdir(parents=True,exist_ok=True)
 variants={};records=[]
 for name,source in [('reference','tests/map_dirty_reference_gba.c'),('incremental','tests/map_dirty_gba.c')]:
  rom,elf,digest=fixture(source,'map_'+name);folder=out/name;folder.mkdir(exist_ok=True);screens=[]
  e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf)
  try:
   for stage in range(1,13):
    for _ in range(600):
     if e.debug()[14]==stage:break
     e.frames(30)
    else:raise AssertionError(('stage timeout',name,stage,e.debug()))
    e.frames(2);p=folder/f'{stage:02}.png';e.shot(p);screens.append(np.asarray(Image.open(p).convert('RGB')))
    e.frames(2,1);e.frames(2)
   variants[name]=screens;records.append({'variant':name,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'production_rom_sha256':digest,'commands':e.log})
  finally:e.close()
 differences=[int(np.any(a!=b,axis=2).sum())for a,b in zip(variants['reference'],variants['incremental'])]
 result={'status':'pass'if not any(differences)else 'fail','kind':'controlled GBA renderer states; genuine save; full repaint compared with dirty-region repaint including hardware cursor','cases':['initial map','facing change','movement','cursor first point','cursor second point','fog opacity','HUD picture movement','picture erased','temporary UI overlay','return to map','tile substitution','map transfer'],'different_pixels_by_case':differences,'records':records,'natural_campaign':'not_run_by_fixture','hardware':'not_run'}
 (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='records'},ensure_ascii=False,indent=2),flush=True)
 assert result['status']=='pass',differences

if __name__=='__main__':main()
