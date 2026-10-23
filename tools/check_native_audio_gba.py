"""Capture the production fixed-point player on an isolated GBA cartridge."""
import hashlib,json,struct,wave
import numpy as np
from gba_fixture import fixture
from drive_opening import ROOT,Emulator

def main():
 rom,elf,production=fixture('tests/native_audio_gba.c','native_audio')
 base=ROOT/'evidence/full_features/native_audio';out=base/'attempts'/hashlib.sha256(rom.read_bytes()).hexdigest()[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf)
 def state():return {'audio':list(struct.unpack('<8I',e.memory(e.symbols['audio_debug'],32))),'midi':list(struct.unpack('<8I',e.memory(e.symbols['native_midi_debug'],32))),'debug':list(e.debug())}
 try:
  e.frames(120);before=state();stream_before=list(struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16)));capture=out/'battle10_gba.wav';e.command('record '+str(capture));e.frames(300);e.command('stop');after=state();stream_after=list(struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16)));e.shot(out/'player.png')
  with wave.open(str(capture))as w:rate=w.getframerate();samples=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2).astype(float)
  seconds=len(samples)/rate;ratio=(after['audio'][3]-before['audio'][3])/(seconds*16384);rms=np.sqrt(np.mean(samples*samples,axis=0)).tolist()
  light=bool(json.loads((ROOT/'build/audio_manifest.json').read_text()).get('gameplay'));implementation='runtime/rm2k/light_midi.c'if light else'runtime/rm2k/native_midi.c';underruns=stream_after[0]-stream_before[0]
  report={'status':'pass'if .999<ratio<1.001 and min(rms)>20 and not after['midi'][3]and not underruns else 'fail','kind':'actual emulated GBA output; original battle10 score; '+('user-approved simplified gameplay timbre'if light else'original supplied SoundFont synthesis'),'original_timbre':not light,'underruns_during_capture':underruns,'source_position_ratio':ratio,'seconds':seconds,'sample_rate':rate,'rms':rms,'before':before,'after':after,'production_rom_sha256':production,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'implementation':implementation,'source_sha256':hashlib.sha256((ROOT/implementation).read_bytes()).hexdigest(),'commands':e.log,'full_track_loop':'not_run','hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(base/'latest_attempt.json').write_text(json.dumps({'report':str((out/'result.json').relative_to(ROOT)),'status':report['status']},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2),flush=True)
  assert report['status']=='pass',report
 finally:e.close()

if __name__=='__main__':main()
