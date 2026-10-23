"""Run the real GBA sample clock across a complete original CC111 music loop."""
import json,struct,hashlib,wave,math
from drive_opening import Emulator,ROOT

def main():
 out=ROOT/'evidence/audio';out.mkdir(exist_ok=True);e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav')
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(360);assert e.debug()[15]==4
  track=next(x for x in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if x['name']=='ダンジョン4');addr=e.symbols['audio_debug'];d=struct.unpack('<8I',e.memory(addr,32));assert d[1]==2
  frames=max(0,math.floor((track['frames']-d[3])/16384*59.7275)-120);e.frames(frames);before=struct.unpack('<8I',e.memory(addr,32));path=out/'native_original_loop.wav';e.command('record '+str(path));e.frames(360);e.command('stop');after=struct.unpack('<8I',e.memory(addr,32));w=wave.open(str(path));seconds=w.getnframes()/w.getframerate();loops=after[4]-before[4];advance=after[3]-before[3]+loops*(track['frames']-track['loop_frame']);ratio=advance/(seconds*16384);assert loops==1,(before,after);assert .999<ratio<1.001,ratio;assert e.debug()[15]==4
  report={'status':'pass','rom_sha256':hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest(),'original_track':track['source'],'source_loop_marker_ms':track['timing']['loop_ms'],'stored_loop_frame':track['loop_frame'],'complete_song_frames':track['frames'],'actual_gba_loop_count':loops,'source_sample_rate_ratio':ratio,'capture':path.name,'seconds':seconds,'commands':e.log,'hardware':'not_run'};(out/'loop_result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False),flush=True)
 finally:e.close()
if __name__=='__main__':main()
