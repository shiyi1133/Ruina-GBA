"""Short recordings through the actual title music room, both simplified modes."""
import array,hashlib,json,math,struct,wave
from drive_opening import ROOT,Emulator

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/music_room_samples'/digest[:12];out.mkdir(parents=True,exist_ok=True);rows=[]
 for quality,label in[(0,'游玩音色_实际录音'),(1,'欣赏音色_实际录音')]:
  e=Emulator()
  try:
   e.frames(30);e.key(1)
   for _ in range(3):e.key(128)
   e.key(1);assert e.debug()[15]==18
   if not quality:e.key(8)
   e.key(1);e.frames(60);assert e.debug()[19]==quality
   before=struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16));path=out/(label+'.wav');e.command('record '+str(path));e.frames(600);e.command('stop');after=struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16));e.frames(2);e.shot(out/(label+'.png'))
   with wave.open(str(path))as w:
    pcm=array.array('h');pcm.frombytes(w.readframes(w.getnframes()));row={'quality':quality,'file':path.name,'frames':w.getnframes(),'rate':w.getframerate(),'channels':w.getnchannels(),'seconds':w.getnframes()/w.getframerate(),'RMS':math.sqrt(sum(int(v)*v for v in pcm)/len(pcm)),'underruns_during_recording':after[0]-before[0]}
   assert row['RMS']>1 and row['underruns_during_recording']==0,row;rows.append(row)
  finally:e.close()
 result={'status':'pass','production_rom_sha256':digest,'kind':'actual production title music room, fresh process and buttons, original first score scene19, both deliberately simplified modes','recordings':rows,'source_audio_timbre':'simplified in both; no original-SoundFont claim','physical_hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
