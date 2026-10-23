"""Compare optimized mono synthesis with its prior stereo-pair implementation.

Both qualities, odd buffer sizes, controller state and actual original-score
positions are observed. This checks an optimization, not original SF2 timbre.
"""
import ctypes as C,hashlib,json,subprocess
import numpy as np
from project_env import ROOT

def main():
 sources=['history/quality_performance_20261022/pre_mono/light_midi.c','runtime/rm2k/light_midi.c'];libs=[]
 bank=C.create_string_buffer((ROOT/'build/light_music/native_soundfont.bin').read_bytes())
 for i,source in enumerate(sources):
  path=ROOT/'build'/f'light_mono_{i}.so'
  subprocess.run(['cc','-std=c99','-O3','-fPIC','-shared','-ffreestanding','-DRUINA_LIGHT_MUSIC','-Iruntime/rm2k',source,'tests/light_music_host_stub.c','-o',str(path)],cwd=ROOT,check=True)
  lib=C.CDLL(str(path));lib.native_midi_init.argtypes=[C.c_void_p];lib.native_midi_start.argtypes=[C.c_void_p];lib.native_midi_render.argtypes=[C.c_void_p,C.c_uint];lib.native_midi_seek.argtypes=[C.c_uint];lib.native_midi_quality.argtypes=[C.c_int];lib.native_midi_init(bank);libs.append(lib)
 manifest=json.loads((ROOT/'build/light_music/audio_manifest.json').read_text());rows=[];samples=0
 for track in manifest['tracks']:
  if track.get('codec')!='simplified original MIDI score':continue
  sequence=C.create_string_buffer((ROOT/'build/light_music'/track['file']).read_bytes())
  for quality in(0,1):
   for where in(0,track['frames']//3,max(0,track['frames']-200)):
    for lib in libs:lib.native_midi_quality(quality);lib.native_midi_start(sequence);lib.native_midi_seek(where)
    for n in(1,2,3,17,63,64,127,513):
     results=[];debug=[]
     for lib in libs:
      output=(C.c_short*(n*2))();lib.native_midi_render(output,n);results.append(bytes(output));debug.append(list((C.c_uint*8).in_dll(lib,'native_midi_debug')))
     assert results[0]==results[1],(track['name'],quality,where,n,'PCM differs')
     assert debug[0]==debug[1],(track['name'],quality,where,n,debug)
     samples+=n
  rows.append({'name':track['name'],'status':'bit-identical','qualities':[0,1],'source_positions':[0,track['frames']//3,max(0,track['frames']-200)]});print(track['name'],'pass',flush=True)
 report={'status':'pass','kind':'host optimization parity using all 99 original scores; not original timbre or GBA timing acceptance','tracks':rows,'frames_compared':samples,
         'sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in sources+['tests/light_music_host_stub.c']}}
 out=ROOT/'evidence/optimization_20261022/music';out.mkdir(parents=True,exist_ok=True);(out/'mono_bit_equivalence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='tracks'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
