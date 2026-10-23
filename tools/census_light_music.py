"""Render every complete simplified score and its loop with both quality modes.
Host continuity/voice bounds do not establish real GBA timing or listening QA.
"""
import ctypes as C,hashlib,json,subprocess,time
from project_env import ROOT

def main():
 target=ROOT/'build/light_music_census.so';subprocess.run(['cc','-std=c99','-O3','-fPIC','-shared','-ffreestanding','-DRUINA_LIGHT_MUSIC','-DRUINA_LIGHT_VOICES=128','-Iruntime/rm2k','runtime/rm2k/light_midi.c','tests/light_music_host_stub.c','-o',str(target)],cwd=ROOT,check=True)
 lib=C.CDLL(str(target));lib.native_midi_init.argtypes=[C.c_void_p];lib.native_midi_start.argtypes=[C.c_void_p];lib.native_midi_render.argtypes=[C.c_void_p,C.c_uint];lib.native_midi_quality.argtypes=[C.c_int]
 bank=C.create_string_buffer((ROOT/'build/light_music/native_soundfont.bin').read_bytes());lib.native_midi_init(bank);manifest=json.loads((ROOT/'build/light_music/audio_manifest.json').read_text());rows=[];pcm=(C.c_short*32768)()
 for track in manifest['tracks']:
  if track.get('codec')!='simplified original MIDI score':continue
  sequence=C.create_string_buffer((ROOT/'build/light_music'/track['file']).read_bytes())
  for quality in(0,1):
   lib.native_midi_quality(quality);lib.native_midi_start(sequence);start=time.monotonic();frames=track['frames']+2*(track['frames']-track['loop_frame']);remaining=frames;digest=hashlib.sha256();peak=peak_position=0
   while remaining:
    n=min(16384,remaining);lib.native_midi_render(pcm,n);digest.update(bytes(pcm)[:n*4]);remaining-=n
    debug=list((C.c_uint*8).in_dll(lib,'native_midi_debug'))
    if debug[1]>peak:peak=debug[1];peak_position=debug[6]
   debug=list((C.c_uint*8).in_dll(lib,'native_midi_debug'));assert not debug[3]and debug[5]>=(2 if track['loop_frame']<track['frames'] else 0),(track['name'],quality,debug)
   row={'name':track['name'],'quality':quality,'source_frames':frames,'peak_voices':debug[1],'peak_source_position':peak_position,'overflows':debug[3],'loops':debug[5],'clipped_channels':debug[4],'PCM_sha256':digest.hexdigest(),'host_seconds':time.monotonic()-start};rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
 report={'status':'pass','kind':'complete host synthesis of all 99 scores plus two loops, both deliberately simplified timbre modes; not GBA timing acceptance','tracks':rows,'max_voices':max(r['peak_voices']for r in rows),'voice_capacity':128,'header_sha256':hashlib.sha256((ROOT/'runtime/rm2k/native_midi.h').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'runtime/rm2k/light_midi.c').read_bytes()).hexdigest(),'bank_sha256':hashlib.sha256(bank.raw[:-1]).hexdigest()};out=ROOT/'evidence/optimization_20261022/music';out.mkdir(parents=True,exist_ok=True);(out/'complete_score_census.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='tracks'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
