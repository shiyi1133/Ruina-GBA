"""Exercise actual use_skill with original data and controlled combatants."""
import hashlib,json,struct
from pathlib import Path
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture

def main():
 generated=ROOT/'build/fixtures/animation_targets';generated.mkdir(parents=True,exist_ok=True)
 override=generated/'battle.c';override.write_text((ROOT/'runtime/rm2k/battle.c').read_text()+'\n'+(ROOT/'tests/battle_animation_target_setup.inc').read_text())
 rom,elf,production=fixture('tests/battle_animation_targets_gba.c','animation_targets',{'battle':str(override)})
 out=ROOT/'evidence/battle_animations_20261023'/hashlib.sha256(rom.read_bytes()).hexdigest()[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf);seen={};screens=[];pressed=False;last_message=None
 try:
  for step in range(14000):
   e.frames(2);d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
   stage=d[18]
   if stage==0x600d:break
   trace=struct.unpack('<16I',e.memory(e.symbols['animation_render_trace'],64))
   if trace[2] and trace[11] and stage in (1,2,3,4) and (stage,trace[0],trace[1]) not in seen:
    key=(stage,trace[0],trace[1]);seen[key]=trace[4]
    path=out/f'stage{stage}_frame{trace[1]:02}.png';e.shot(path)
    if stage==3:screens.append(path)
   signature=(d[21],d[16],stage)
   if d[15]==1 and signature!=last_message:
    # The real engine requires a new A edge to dismiss the source message.
    e.frames(2,1);e.frames(2);last_message=signature
   elif stage in (0x100,0x101,0x102,0x103):e.frames(2,1);e.frames(2);last_message=None
  else:raise AssertionError(('skill stages not finished',e.debug()))
  expected={1:(46,2),2:(62,16),3:(78,112),4:(68,1)}
  for stage,(aid,mask)in expected.items():
   rows=[(key,value)for key,value in seen.items()if key[0]==stage];assert rows and all(k[1]==aid and value==mask for k,value in rows),(stage,rows)
  if screens:
   images=[Image.open(p).convert('RGB').resize((720,480),Image.Resampling.NEAREST)for p in screens]
   images[0].save(out/'爆炎投射.gif',save_all=True,append_images=images[1:],duration=100,loop=0)
  result={'status':'pass','production_ROM_sha256':production,'fixture_ROM_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'scope':'actual production use_skill and formulas with controlled original enemies, legal original magic weapon and stats; real A presses only','cases':{str(k):{'animation':v[0],'target_mask':v[1],'observed_frames':sum(s[0]==k for s in seen)}for k,v in expected.items()},'frames_observed':len(seen),'GIF':'visual frame sequence, not real-time performance evidence','physical_hardware':'not_run','full_campaign':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(ROOT/'evidence/battle_animations_20261023/targets_latest.json').write_text(json.dumps({'report':str(out/'result.json'),'status':'pass'},ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
 finally:e.close()
if __name__=='__main__':main()
