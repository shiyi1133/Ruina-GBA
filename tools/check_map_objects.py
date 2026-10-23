"""Original-size charset crops, independent OBJ palette banks and UI return."""
import hashlib,json,struct,zipfile,zlib
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture
from project_env import ARCHIVE
from portrait_assets import logical

def main():
 rom,elf,digest=fixture('tests/map_objects_gba.c','map_objects',{'video':'tests/native_palette_video.c'})
 out=ROOT/'evidence/hardware_scroll/objects';out.mkdir(parents=True,exist_ok=True)
 manifest=json.loads((ROOT/'build/asset_manifest.json').read_text());names=manifest['images'];resources=[v['image']for v in manifest['resources']if v['kind']==3]
 e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf);screens=[];checks={}
 try:
  for stage in range(1,4):
   for _ in range(1200):
    if e.debug()[14]==stage:break
    e.frames(1)
   else:raise AssertionError(('stage',stage))
   e.frames(2);p=out/f'stage_{stage}.png';e.shot(p);a=np.asarray(Image.open(p).convert('RGB'));screens.append(a)
   if stage!=2:
    different=[]
    for n,image in enumerate(resources):
     im=Image.open(ROOT/'build'/(names[image]+'_palette.png'));p=np.asarray(im)[64:96,24:48];rgb=np.asarray(im.convert('RGB'))[64:96,24:48];actual=a[n//3*48:n//3*48+32,n%3*72:n%3*72+24]
     different.append(int(np.any((actual>>3)!=(rgb>>3),axis=2)[p!=0].sum()))
    checks[f'nine_charset_palettes_exact_stage_{stage}']=not any(different)
    checks[f'nine_charsets_visible_stage_{stage}']=struct.unpack('<I',e.memory(e.symbols['map_actor_count'],4))[0]==9
    for slot,(x,y)in [(25,(60,130)),(20,(128,130))]:
     image=struct.unpack('<h',e.memory(e.symbols['game']+35716+slot*30,2))[0];im=Image.open(ROOT/'build'/(names[image]+'_palette.png'));idx=np.asarray(im);rgb=np.asarray(im.convert('RGB'));actual=a[y:y+im.height,x:x+im.width]
     checks[f'original_HUD_palette_{slot}_stage_{stage}']=bool(np.array_equal((actual>>3)[idx!=0],(rgb>>3)[idx!=0]))
   e.frames(2,1);e.frames(2)
  with zipfile.ZipFile(ARCHIVE)as z:
   name=next(n for n in z.namelist()if logical(n).endswith('/FaceSet/顔絵主役.xyz'));raw=z.read(name);w,h=struct.unpack_from('<HH',raw,4);d=zlib.decompress(raw[8:]);pal=np.frombuffer(d[:768],np.uint8).reshape(256,3);p=np.frombuffer(d[768:],np.uint8).reshape(h,w)[:48,:48];rgb=pal[p]
  checks['portrait_after_tiled_map_keeps_original_palette']=bool(np.array_equal((screens[1][20:68,8:56]>>3)[p!=0],(rgb>>3)[p!=0]))
  checks['return_from_portrait_restores_map_objects']=bool(np.array_equal(screens[0],screens[2]))
  result={'status':'pass'if all(checks.values())else'fail','production_rom_sha256':digest,'checks':checks,'kind':'controlled cartridge, native charset pixels and original 48x48 source portrait, real buttons','commands':e.log,'hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2),flush=True);assert result['status']=='pass',checks
 finally:e.close()

if __name__=='__main__':main()
