"""One-shot score completion and replay via real music-room buttons."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();tracks=[t for t in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if t['kind']=='music'];index=next(i for i,t in enumerate(tracks)if t['name']=='J戦闘終了1');track=tracks[index];assert track['loop_frame']>=track['frames'];out=ROOT/'evidence/optimization_20261022/music_room_replay'/digest[:12];out.mkdir(parents=True,exist_ok=True);e=Emulator();rows=[]
 def position():return struct.unpack('<8I',e.memory(e.symbols['audio_debug'],32))[3]
 try:
  e.frames(30);e.key(1)
  for _ in range(3):e.key(128)
  e.key(1);assert e.debug()[15]==18
  for _ in range(index):e.key(128)
  for quality in(1,0):
   assert e.debug()[19]==quality
   e.key(1);e.frames(400);ended=position();assert ended>=track['frames'],(ended,track)
   e.frames(2);e.shot(out/f'ended_{quality}.png');e.key(1);restarted=position();assert e.debug()[23]==0 and 0<restarted<track['frames'],('one-shot not replayed',quality,ended,restarted,e.debug())
   e.frames(60);assert position()>restarted;e.shot(out/f'replaying_{quality}.png');rows.append({'quality':quality,'ended_source_frame':ended,'restarted_source_frame':restarted,'real_replay_advances':True})
   if quality:e.frames(400);e.key(8);e.frames(30)
  result={'status':'pass','production_rom_sha256':digest,'kind':'actual title music-room buttons, original one-shot MIDI; completion/replay in both simplified modes','track':track['name'],'checks':rows,'physical_hardware':'not_run','commands':e.log};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2))
 except Exception as error:
  e.shot(out/'stopped.png');(out/'failed_attempt.json').write_text(json.dumps({'status':'fail','production_rom_sha256':digest,'error':repr(error),'debug':e.debug(),'commands':e.log},ensure_ascii=False,indent=2));raise
 finally:e.close()
if __name__=='__main__':main()
