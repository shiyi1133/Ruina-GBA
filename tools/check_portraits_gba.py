"""Compare real GBA OBJ portrait pixels to the user's original XYZ data."""
import hashlib,json,struct,zipfile,zlib
from pathlib import Path
import numpy as np
from PIL import Image
from portrait_assets import logical
from project_env import ARCHIVE
from gba_fixture import fixture
from drive_opening import ROOT,Emulator

def main():
 manifest=json.loads((ROOT/'build/asset_manifest.json').read_text());labels=manifest['images'];original={}
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()}
  for sheet,path in enumerate(sorted(n for n in names if '/FaceSet/'in n and n.endswith('.xyz'))):
   raw=z.read(names[path]);w,h=struct.unpack_from('<HH',raw,4);d=zlib.decompress(raw[8:]);pal=np.frombuffer(d[:768],np.uint8).reshape(256,3);pixels=np.frombuffer(d[768:],np.uint8).reshape(h,w)
   for i in range(16):
    name='hero'+str(i)if Path(path).stem=='顔絵主役'else f'face{sheet}_{i}';p=pixels[i//4*48:i//4*48+48,i%4*48:i%4*48+48]
    original[labels.index(name)]=(pal[p],p!=0)
 rom,elf,digest=fixture('tests/portraits_gba.c','portraits')
 out=ROOT/'evidence/full_features/portraits'/hashlib.sha256(rom.read_bytes()).hexdigest()[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf);checks={}
 def until(n):
  for _ in range(1000):
   if e.debug()[14]==n:return
   e.frames(1)
  raise AssertionError((n,e.debug()))
 def shot(name):
  e.frames(2);p=out/(name+'.png');e.shot(p);return np.asarray(Image.open(p).convert('RGB'))
 def verify(screen,id,x,y):
  rgb,mask=original[id];actual=screen[y:y+48,x:x+48];return bool(np.array_equal(actual[mask]>>3,rgb[mask]>>3))
 try:
  until(1);checks['original_48px_hero_original_colors']=verify(shot('hero_48px'),labels.index('hero0'),8,20)
  e.frames(2,1);e.frames(2);until(2);screen=shot('four_original_faces')
  checks['four_faces_without_palette_conflict']=all(verify(screen,labels.index('hero'+str(i)),7+i*59,1)for i in range(4))
  e.frames(2,1);e.frames(2);until(3);npc=e.debug()[13]
  checks['different_sheet_palette_switch']=verify(shot('companion_48px'),npc,8,20)
  e.frames(2,1);e.frames(2);until(4);a=shot('portrait_removed')
  checks['no_portrait_left_on_next_scene']=len(np.unique(a.reshape(-1,3),axis=0))==1
  e.frames(2,1);e.frames(2);until(5);e.frames(120)
  checks['dialogue_uses_original_face']=verify(shot('dialogue_original_face'),npc,8,62)
  result={'status':'pass'if all(checks.values())else 'fail','kind':'actual GBA OBJ pixels compared at RGB555 precision to original 48x48 source faces','production_rom_sha256':digest,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'checks':checks,'commands':e.log,'hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'report':str((out/'result.json').relative_to(ROOT)),'status':result['status']},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2),flush=True)
  assert result['status']=='pass',checks
 finally:e.close()

if __name__=='__main__':main()
