"""Status browsing must stay responsive without repainting an idle screen."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator
from save_observation import persistent_view

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/status_ui'/digest[:12];out.mkdir(parents=True,exist_ok=True)
 save=ROOT/'history/legacy_checkpoint_v2.sav';e=Emulator(save)
 def value(name):return struct.unpack('<I',e.memory(e.symbols[name],4))[0]
 def presents():return struct.unpack('<I',e.memory(e.symbols['video_metrics']+16,4))[0]+struct.unpack('<I',e.memory(e.symbols['map_video_metrics']+8,4))[0]
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(180);assert e.debug()[15]==4
  before=persistent_view(e.memory(e.symbols['game'],39704));assert len(before['party'])>2
  e.key(8);assert e.debug()[15]==2;e.key(1);e.frames(2);e.shot(out/'first.png')
  initial=presents();changes=0;first_hash=e.command('lcdhash').split()[1]
  for _ in range(180):
   e.frames(1);current=presents();changes+=current!=initial;initial=current
  assert changes==0,changes
  assert e.command('lcdhash').split()[1]==first_hash
  e.key(128);e.frames(2);e.shot(out/'next.png');assert presents()>initial and e.command('lcdhash').split()[1]!=first_hash
  e.key(64);e.frames(2);e.shot(out/'back.png');assert (out/'first.png').read_bytes()==(out/'back.png').read_bytes()
  assert (out/'first.png').read_bytes()!=(out/'next.png').read_bytes()
  e.key(2);e.frames(120);assert e.debug()[15]==4
  assert persistent_view(e.memory(e.symbols['game'],39704))==before
  report={'status':'pass','production_rom_sha256':digest,'kind':'production ROM, genuine ordinary campaign SAV, actual buttons, actual LCD hashes and bitmap/UI/BG presentation counters','idle_hardware_frames':180,'idle_presentations':changes,'browse_changes_visible':True,'up_returns_same_pixels':True,'persistent_player_state_unchanged':True,'hardware':'not_run','commands':e.log}
  (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
