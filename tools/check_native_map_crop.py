"""GBA pixels versus exact native-size indexed-art crops, excluding UI arrows."""
import hashlib,json
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture

def main():
 rom,elf,digest=fixture('tests/native_map_crop_gba.c','native_map_crop',{'video':'tests/native_palette_video.c'})
 out=ROOT/'evidence/hardware_scroll/native_crop';out.mkdir(parents=True,exist_ok=True)
 source=Image.open(ROOT/'build/cave_palette.png').convert('RGB');assert source.size==(320,240)
 e=Emulator(rom=rom,elf=elf);rows=[]
 mask=np.ones((160,240),bool)
 for x,y in [(116,2),(230,76),(116,150),(2,76)]:mask[y:y+8,x:x+8]=False
 try:
  for stage,(x,y)in enumerate([(0,0),(80,80),(8,16)],1):
   for _ in range(1000):
    if e.debug()[14]==stage:break
    e.frames(1)
   else:raise AssertionError(('stage',stage))
   e.frames(2);path=out/f'crop_{x}_{y}.png';e.shot(path)
   actual=np.asarray(Image.open(path).convert('RGB'))>>3;expected=np.asarray(source.crop((x,y,x+240,y+160)))>>3
   different=int(np.any(actual!=expected,axis=2)[mask].sum());rows.append({'camera':[x,y],'compared_pixels':int(mask.sum()),'different_pixels':different})
   e.frames(2,1);e.frames(2)
  manifest=json.loads((ROOT/'build/asset_manifest.json').read_text());resources=[manifest['image_storage'][r['image']]for r in manifest['resources']if r['kind']in(1,2,3)]
  checks={'native_crop_matches_GBA_pixels':not any(r['different_pixels']for r in rows),'panoramas_chipsets_charsets_keep_original_dimensions':all((r['width'],r['height'])==(r['stored_width'],r['stored_height'])for r in resources)}
  result={'status':'pass'if all(checks.values())else'fail','production_rom_sha256':digest,'checks':checks,'crops':rows,'native_resources_checked':len(resources),'color_precision':'existing shared game palette at GBA RGB555; this is spatial fidelity, not original 256-color fidelity','commands':e.log,'hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2),flush=True);assert result['status']=='pass',checks
 finally:e.close()

if __name__=='__main__':main()
