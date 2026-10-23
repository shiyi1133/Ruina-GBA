"""Real B-menu playback selection, cancellation and paused persistent state."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator
from save_observation import persistent_view

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();save=ROOT/'tests/fixtures/before_dead_knight.sav';original=hashlib.sha256(save.read_bytes()).hexdigest();e=Emulator(save);out=ROOT/'evidence/animation_smooth_20261023';checks=[]
 def selected():return struct.unpack('<I',e.memory(e.symbols['animation_full_frames'],4))[0]
 def settings():
  e.key(2);assert e.debug()[15]==2 and e.debug()[17]==8,e.debug()
  for _ in range(6):e.key(128)
  e.key(1)
  for _ in range(10):
   if e.debug()[15]==2 and e.debug()[17]==3:return
   assert e.debug()[15]==1,e.debug();e.key(1)
  raise AssertionError(('settings dialog',e.debug()))
 def leave():
  assert e.debug()[15]==2 and e.debug()[17]==8,e.debug();e.key(2);assert e.debug()[15]==4,e.debug()
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(240);assert e.debug()[15]==4,e.debug();before=persistent_view(e.memory(e.symbols['game'],39704));assert selected()==0
  settings();assert e.debug()[16]==0;e.shot(out/'animation_playback_options.png');e.key(128);e.key(1);assert selected()==1;leave();checks.append('complete-frames selection')
  settings();assert e.debug()[16]==1;e.key(2);assert selected()==1;leave();checks.append('cancel preserves setting')
  settings();e.key(64);e.key(1);assert selected()==0;leave();checks.append('original-time selection')
  assert persistent_view(e.memory(e.symbols['game'],39704))==before
  assert hashlib.sha256(save.read_bytes()).hexdigest()==original
  e.shot(out/'animation_settings_return.png');r={'status':'pass','production_ROM_sha256':digest,'checks':checks,'persistent_game_unchanged':True,'original_SAV_unchanged':True,'setting_scope':'current process, original-time default','physical_hardware':'not_run'};(out/'settings.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
