"""Actual LCD cell visibility, clean restoration and source-preserving storage.
Controlled frames use a separate cartridge, not writes to a running game.
"""
import hashlib,json,struct
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from inspect_lcf import data_root,array,integer,text
from gba_fixture import fixture

def main():
 db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1];cases=[]
 for aid,a in array(db[19]):
  frames=array(a.get(12,b''));best=None
  for fid,f in frames:
   valid=[c for _,c in array(f.get(1,b''))if integer(c.get(1),1)and integer(c.get(10),0)<100]
   score=0
   for c in valid:
    def signed(v):return v-0x100000000 if v>=0x80000000 else v
    zoom=integer(c.get(5),100);w=96*zoom*3//400;h=96*zoom*2//300
    x=120+signed(integer(c.get(3),0))*3//4-w//2;y=53+signed(integer(c.get(4),0))*2//3-h//2
    score+=max(0,min(240,x+w)-max(0,x))*max(0,min(160,y+h)-max(0,y))*(100-integer(c.get(10),0))
   if score and(best is None or score>best[0]):best=(score,fid-1)
  if a.get(2,b'')and best:cases.append((aid,best[1],text(a.get(1,b''))))
 header='static const int animation_cases[][2]={'+','.join('{%d,%d}'%c[:2]for c in cases)+'};\n'
 (ROOT/'build/battle_animation_cases.h').write_text(header)
 rom,elf,production=fixture('tests/battle_animation_gallery_gba.c','battle_animation_gallery')
 digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/battle_animations_20261023'/digest[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf);rows=[]
 def until(stage):
  for _ in range(2000):
   if e.debug()[14]==stage:return
   assert e.debug()[0]!=0x4641554c,e.debug();e.frames(2)
  raise AssertionError((stage,e.debug()))
 def shot(path):e.shot(path);return np.asarray(Image.open(path).convert('RGB'))
 def press():e.frames(2,1);e.frames(2)
 try:
  until(1);base=shot(out/'clean_battle.png');press()
  for n,(aid,frame,name)in enumerate(cases):
   until(n+2);screen=shot(out/f'animation_{aid:03d}.png');trace=struct.unpack('<16I',e.memory(e.symbols['animation_render_trace'],64));different=int(np.count_nonzero(np.any(screen!=base,axis=2)))
   rows.append({'id':aid,'name':name,'source_frame':frame,'visible_changed_LCD_pixels':different,'trace':trace});assert different>0,rows[-1]
   press();until(0x10000+n);restored=shot(out/'restored.png');assert np.array_equal(restored,base),('trails',aid,int(np.count_nonzero(restored!=base)))
   press()
  until(0x600d)
  result={'status':'pass','production_ROM_sha256':production,'fixture_ROM_sha256':digest,'animation_records':len(array(db[19])),'visual_records_checked':len(rows),'clean_background_after_every_animation':True,'input':'real buttons in separately compiled controlled cartridge','memory':'read-only','hardware':'not_run','full_campaign':'not_run','rows':rows}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(ROOT/'evidence/battle_animations_20261023/gallery_latest.json').write_text(json.dumps({'report':str(out/'result.json'),'status':'pass'},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'},ensure_ascii=False))
 finally:e.close()
if __name__=='__main__':main()
