"""Observe reduced GBA effects through real buttons and rendered pixels."""
import hashlib,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from gba_fixture import fixture
from drive_opening import ROOT,Emulator

def main():
 rom,elf,production=fixture('tests/presentation_gba.c','presentation')
 out=ROOT/'evidence/full_features/presentation'/(hashlib.sha256(rom.read_bytes()).hexdigest()[:12]+'_'+hashlib.sha256(Path(__file__).read_bytes()).hexdigest()[:8])
 out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf);checks={};captures={}
 def stage():return e.debug()[14]
 def until(n):
  for _ in range(1500):
   if stage()==n:return
   e.frames(1)
  raise AssertionError(('stage not reached',n,e.debug()))
 def shot(name):
  # A completed CPU flip can still be partway through LCD scanout.
  e.frames(2)
  p=out/(name+'.png');e.shot(p)
  a=np.asarray(Image.open(p).convert('RGB')).astype(float)
  captures[name]={'file':p.name,'mean':float(a.mean()),'nonblack':int(np.any(a>0,axis=2).sum())}
  return a
 def press():e.frames(2,1);e.frames(1)
 try:
  until(1);before=shot('before');press()
  until(3);black=shot('immediate_black')
  checks['erase_cuts_to_true_black']=not black.any()
  checks['erase_adds_no_transition_wait']=e.debug()[13]==0
  press();until(4);dialogue=shot('dialogue_over_black')
  checks['dialogue_after_erasing_readable']=bool(dialogue.any())
  press();hidden=[]
  # Sample while the production renderer builds the new image. The hardware
  # shade must keep all its layers black, rather than revealing a partial draw.
  for _ in range(1000):
   current=stage()
   if current==6:break
   if current==5:
    e.frames(2)
    if stage()==5:
     p=out/'preparing_behind_black.png';e.shot(p);a=np.asarray(Image.open(p).convert('RGB'));hidden.append(not bool(a.any()))
   e.frames(1)
  else:raise AssertionError(('new scene did not finish',e.debug()))
  visible=shot('new_scene')
  checks['new_image_prepared_behind_black']=bool(hidden)and all(hidden)
  checks['new_image_revealed_without_fade']=bool(visible.any())and e.debug()[13]==0
  press();until(7);flash=shot('simple_flash');until(8);normal=shot('flash_finished')
  checks['brief_flash_then_restored']=flash.mean()>normal.mean()
  press();until(9);weather=shot('static_rain')
  checks['weather_kept_as_static_overlay']=bool(np.any(weather!=normal))
  press();until(11);reset=shot('reset_visible')
  checks['reset_releases_brightness']=bool(reset.any()) and not struct.unpack('<H',e.memory(0x04000050,2))[0]
  assert not e.debug()[1],e.debug()
  report={'status':'pass'if all(checks.values())else 'fail','kind':'isolated cartridge, production black-cut renderer, real buttons and observed pixels','hidden_draw_samples':len(hidden),'production_rom_sha256':production,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'checks':{k:bool(v)for k,v in checks.items()},'captures':captures,'commands':e.log,'full_campaign':'not_run','hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
  (out.parent/'latest_attempt.json').write_text(json.dumps({'report':str((out/'result.json').relative_to(ROOT)),'status':report['status']},ensure_ascii=False,indent=2))
  print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2),flush=True)
  assert report['status']=='pass',checks
 except Exception as error:
  e.shot(out/'failed.png')
  (out/'failure.json').write_text(json.dumps({'status':'fail','error':str(error),'commands':e.log,'debug':e.debug()},ensure_ascii=False,indent=2))
  raise
 finally:e.close()

if __name__=='__main__':main()
