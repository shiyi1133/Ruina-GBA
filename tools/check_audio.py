"""Capture actual mGBA audio, compare to decoded ROM data without game writes."""
import sys,struct,json,hashlib,wave,audioop
import numpy as np
from drive_opening import Emulator,ROOT

def main():
 out=ROOT/'evidence/audio';out.mkdir(exist_ok=True);e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav')
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(360)
  assert e.debug()[15]==4,e.debug();addr=e.symbols['audio_debug'];before=struct.unpack('<8I',e.memory(addr,32));assert before[1]==2,before
  audio=out/'cave_native_capture.wav';e.command('record '+str(audio));e.frames(180);receipt=e.command('stop');after=struct.unpack('<8I',e.memory(addr,32))
  w=wave.open(str(audio));rate=w.getframerate();actual=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,2).astype(float)
  entry=next(x for x in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if x['name']=='ダンジョン4');b=(ROOT/'build/audio_cache'/('0_%08x.adpcm'%int(hash_name(entry['name'])))).read_bytes()
  # Independent Python IMA decode of the exact ROM payload, then 2x repeat to
  # compare against mGBA's physical 32768-Hz output clock.
  raw=np.frombuffer(b,dtype=np.uint8);left_codes=(raw[::2]&240)|(raw[1::2]>>4);right_codes=(raw[::2]<<4)|(raw[1::2]&15)
  left=np.frombuffer(audioop.adpcm2lin(left_codes.tobytes(),2,(0,0))[0],dtype='<i2');right=np.frombuffer(audioop.adpcm2lin(right_codes.tobytes(),2,(0,0))[0],dtype='<i2');samples=np.column_stack([left,right])[before[3]-300:after[3]+200]
  expected=np.repeat(np.asarray(samples,dtype=float),2,axis=0);expected=(expected*(90*256//100)/256)//256*256
  comparisons=[]
  for ch in range(2):
   a=actual[:,ch];x=expected[:,ch];size=1<<(len(x)+len(a)-2).bit_length();corr=np.fft.irfft(np.fft.rfft(x,size)*np.fft.rfft(a[::-1],size),size)[len(a)-1:len(x)];start=int(np.argmax(corr));s=x[start:start+len(a)];comparisons.append(float(np.corrcoef(a,s)[0,1]))
  elapsed=len(actual)/rate;advance=after[3]-before[3];ratio=advance/(elapsed*16384);rms=np.sqrt(np.mean(actual**2,axis=0));assert all(v>20 for v in rms),rms;assert .999<ratio<1.001,ratio;assert min(comparisons)>.96,comparisons
  result={'status':'pass','kind':'actual emulated GBA stereo output compared to ROM samples','rom_sha256':hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest(),'capture':audio.name,'seconds':elapsed,'output_rate':rate,'source_position_rate_ratio':ratio,'left_right_correlation':comparisons,'rms':rms.tolist(),'original_track':entry['source'],'source_sha256':entry['source_sha256'],'keys_and_read_only_observations':e.log,'hardware':'not_run','whole_track_loop':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='keys_and_read_only_observations'},ensure_ascii=False),flush=True)
 finally:e.close()
def hash_name(s):
 h=2166136261
 for c in s.encode('cp932'):h=((h^c)*16777619)&0xffffffff
 return h
if __name__=='__main__':main()
