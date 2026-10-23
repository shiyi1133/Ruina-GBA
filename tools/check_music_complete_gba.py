"""Play every entire score plus two loops on the emulated ARM7 and real IRQs.
This goes beyond the peak excerpts, but remains an isolated playback cart,
not listening QA, combined gameplay coverage or physical hardware acceptance.
"""
import hashlib,json,math,struct,time
from project_env import ROOT
from drive_opening import Emulator
from gba_fixture import fixture

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 digest=sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba');manifest=json.loads((ROOT/'build/audio_manifest.json').read_text());tracks=[t for t in manifest['tracks']if t['kind']=='music'];cases=[(t,q)for t in tracks for q in(0,1)];assert len(cases)==210
 config='static const unsigned music_complete[][2]={\n'+''.join('{%d,%d},\n'%(t['id'],q)for t,q in cases)+'};\n';(ROOT/'build/music_complete_config.h').write_text(config)
 rom,elf,bound=fixture('tests/music_complete_gba.c','complete_music');assert bound==digest;out=ROOT/'evidence/optimization_20261022/music/complete_GBA'/digest[:12];out.mkdir(parents=True,exist_ok=True);e=Emulator(rom=rom,elf=elf);rows=[];start=time.monotonic();fps=16777216/280896
 def read(name,n):return struct.unpack('<%dI'%n,e.memory(e.symbols[name],n*4))
 def progress(status):
  result={'status':status,'production_rom_sha256':digest,'fixture_sha256':sha(rom),'kind':'isolated actual emulated GBA ARM7, timer IRQ and queue: each complete original score and two loops, both simplified timbre modes','completed':len(rows),'total':len(cases),'wall_seconds':time.monotonic()-start,'cases':rows,'scope':'full playback timing; no emulated state writes, no instant states; not whole-campaign or physical-hardware QA','hardware':'not_run'}
  (out/'progress.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
 try:
  for i,(t,q)in enumerate(cases):
   for _ in range(20000):
    if e.debug()[14]==i+1:break
    e.frames(1)
   else:raise AssertionError(('stage',i,e.debug()))
   begin=time.monotonic();a=read('audio_debug',8);base=e.debug()[13];loop=max(0,t['frames']-t['loop_frame']);wanted=t['frames']+2*loop
   # Enough real LCD frames to consume the full intro and two further loops.
   frames=math.ceil(wanted/16384*fps);done=0
   while done<frames:
    n=min(1800,frames-done);e.frames(n);done+=n
    if read('audio_stream_debug',4)[0]!=base:raise AssertionError(('underrun',t['name'],q,done,read('audio_stream_debug',4),base))
   b=read('audio_debug',8);m=read('native_midi_debug',8);s=read('audio_stream_debug',4);advanced=b[3]-a[3]+(b[4]-a[4])*loop;expected=frames/fps*16384
   if not loop:expected=min(expected,max(0,t['frames']-a[3]))
   ratio=advanced/expected if expected else 1;is_midi=t.get('codec')=='simplified original MIDI score';overflow=m[3]if is_midi else 0
   row={'name':t['name'],'id':t['id'],'quality':q,'hardware_frames':frames,'source_frames_expected':expected,'source_frames_consumed':advanced,'source_clock_ratio':ratio,'completed_loops':b[4]-a[4],'underruns_since_initial_priming':s[0]-base,'voice_overflows':overflow,'peak_voices':m[1]if is_midi else 0,'wall_seconds':time.monotonic()-begin,'status':'pass'if .999<=ratio<=1.001 and not overflow and s[0]==base else'fail'};rows.append(row);progress('running'if row['status']=='pass'else'fail');print(json.dumps(row,ensure_ascii=False),flush=True);assert row['status']=='pass',row
   e.frames(2,1);e.frames(2)
  assert sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba')==digest
  result=progress('pass');(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='cases'},ensure_ascii=False,indent=2),flush=True)
 except Exception as error:
  result=progress('fail');result['error']=repr(error);(out/'failed_attempt.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));raise
 finally:e.close()
if __name__=='__main__':main()
