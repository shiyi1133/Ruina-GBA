"""Bound original soundtrack polyphony without dropping voices or notes.

Host execution observes the production synthesizer's control/envelope state.
No PCM comparison or GBA timing acceptance is implied by this census.
"""
import ctypes as C,hashlib,json,subprocess,time
from pathlib import Path
from project_env import ROOT

def main():
 out=ROOT/'evidence/optimization_20261022/polyphony';out.mkdir(parents=True,exist_ok=True)
 library=ROOT/'build/native_midi_census.so'
 subprocess.run(['cc','-O3','-fPIC','-shared','-ffreestanding','-DNATIVE_VOICE_LIMIT=1024',
                 '-Iruntime/rm2k','runtime/rm2k/native_midi.c','-o',str(library)],cwd=ROOT,check=True)
 lib=C.CDLL(str(library));lib.native_midi_init.argtypes=[C.c_void_p];lib.native_midi_start.argtypes=[C.c_void_p]
 lib.native_midi_render.argtypes=[C.c_void_p,C.c_uint]
 bank=C.create_string_buffer((ROOT/'history/quality_performance_20261022/baseline/build/native_music/native_soundfont.bin').read_bytes())
 lib.native_midi_init(bank);manifest=json.loads((ROOT/'build/native_music/manifest.json').read_text());rows=[]
 for track in manifest['tracks']:
  sequence=C.create_string_buffer((ROOT/'build/native_music'/track['file']).read_bytes())
  lib.native_midi_start(sequence);start=time.monotonic()
  # The saved loop-state includes release tails at the loop point. Observe
  # three complete repeats as well as the introduction.
  n=track['frames']+3*(track['frames']-track['loop_frame'])
  lib.native_midi_render(None,n)
  debug=list((C.c_uint*8).in_dll(lib,'native_midi_debug'))
  row={'name':track['name'],'samples_observed':n,'peak_voices':debug[1],'overflows':debug[3],
       'loops':debug[5],'host_seconds':time.monotonic()-start,'sequence_sha256':hashlib.sha256(sequence.raw[:-1]).hexdigest()}
  rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 result={'status':'pass'if all(not r['overflows']for r in rows)else'fail','kind':'host control/envelope census; not GBA timing or listening acceptance',
         'host_capacity':1024,'max_original_voices':max(r['peak_voices']for r in rows),'tracks':rows,
         'sources':{'runtime/rm2k/native_midi.c':hashlib.sha256((ROOT/'runtime/rm2k/native_midi.c').read_bytes()).hexdigest()},
         'soundfont_bank_sha256':hashlib.sha256(bank.raw[:-1]).hexdigest()}
 (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='tracks'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
