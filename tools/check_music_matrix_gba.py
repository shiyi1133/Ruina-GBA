"""Actual GBA queue/clock/audio observations near every score's voice peak.
The separate host census covers complete scores and two loops. This cartridge
is a playback timing spot check of both timbre modes, not a gameplay campaign.
"""
import hashlib,json,struct,wave,sys
import numpy as np
from project_env import ROOT
from gba_fixture import fixture
from drive_opening import Emulator

def main():
 census=json.loads((ROOT/'evidence/optimization_20261022/music/complete_score_census.json').read_text());meta=json.loads((ROOT/'build/audio_manifest.json').read_text());tracks={t['name']:t for t in meta['tracks']if t.get('codec')=='simplified original MIDI score'}
 selected=sys.argv[sys.argv.index('--track')+1]if '--track'in sys.argv else None
 original_pitches='--original-pitches'in sys.argv
 rows=[(tracks[r['name']],r)for r in census['tracks']if selected is None or r['name']==selected];config=['static const unsigned music_matrix[][4]={'];assert rows
 if original_pitches:
  from music_pitch_usage import collect
  usage=collect();all_tracks={t['name']:t for t in meta['tracks']if t['kind']=='music'};peaks={r['name']:r for r in census['tracks']if r['quality']==0};rows=[]
  for c in usage['cases']:
   if c['pitch']==100:continue
   assert c['name']in all_tracks,c
   peak=dict(peaks.get(c['name'],{'quality':0,'peak_source_position':32768,'peak_voices':0}));peak['pitch']=c['pitch'];rows.append((all_tracks[c['name']],peak))
  (ROOT/'evidence/optimization_20261022/music/original_pitch_usage.json').write_text(json.dumps(usage,ensure_ascii=False,indent=2))
 for t,r in rows:config.append('{%d,%d,%d,%d},'%(t['id'],r['quality'],max(0,r['peak_source_position']-32768),r.get('pitch',100)))
 (ROOT/'build/music_matrix_config.h').write_text('\n'.join(config+['};']))
 bank_digest=hashlib.sha256((ROOT/'build/audio.bin').read_bytes()).hexdigest();rom,elf,production=fixture('tests/music_matrix_gba.c','music_pitch_matrix'if original_pitches else'music_matrix_subset'if selected else'music_matrix');digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/music/gba_matrix'/digest[:12];out.mkdir(parents=True,exist_ok=True);e=Emulator(rom=rom,elf=elf);results=[]
 def read(name,n):return struct.unpack('<%dI'%n,e.memory(e.symbols[name],n*4))
 try:
  for i,(t,peak)in enumerate(rows):
   for _ in range(20000):
    if e.debug()[14]==i+1:break
    e.frames(10)
   else:raise AssertionError(('seek stage timeout',i,e.debug()))
   e.frames(60);a=read('audio_debug',8);s=read('audio_stream_debug',4);path=out/('%03d_%d_%d.wav'%(t['id'],peak['quality'],peak.get('pitch',100)));e.command('record '+str(path));e.frames(180);e.command('stop');b=read('audio_debug',8);u=read('audio_stream_debug',4);m=read('native_midi_debug',8)
   elapsed=180*280896/16777216;expected=elapsed*16384*peak.get('pitch',100)/100
   if t['loop_frame']<t['frames']:advance=b[3]-a[3]+(b[4]-a[4])*(t['frames']-t['loop_frame'])
   else:expected=min(expected,max(0,t['frames']-a[3]));advance=max(0,b[3]-a[3])
   ratio=advance/expected if expected else 1
   with wave.open(str(path))as w:pcm=np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').astype(np.float64);rms=float(np.sqrt(np.mean(pcm*pcm)))
   row={'name':t['name'],'track_id':t['id'],'quality':peak['quality'],'pitch_percent':peak.get('pitch',100),'seek_source_frame':max(0,peak['peak_source_position']-32768),'host_peak_voices':peak['peak_voices'],'GBA_peak_voices':m[1],'underruns_during_capture':u[0]-s[0],'source_clock_ratio':ratio,'voice_overflows':m[3],'captured_RMS':rms,'status':'pass'if u[0]==s[0]and not m[3]and .995<=ratio<=1.005 else'fail'};results.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
   if row['status']=='pass'and t['name']not in('battle10','村1','INT03','神秘3','DS-ba03'):path.unlink()
   (out/'progress.json').write_text(json.dumps(results,ensure_ascii=False,indent=2));e.frames(2,1);e.frames(2)
  result={'status':'pass'if all(r['status']=='pass'for r in results)else'fail','kind':'actual emulated GBA, '+('original non-100 pitch uses'if original_pitches else'selected score '+selected if selected else'each original score')+' near its host-observed polyphony peak, '+('gameplay timbre'if original_pitches else'both simplified timbre modes'),'production_rom_sha256':production,'fixture_sha256':digest,'source_bank_sha256':bank_digest,'cases':results,'scope':'three seconds per case after warmup; complete score/loops checked on host separately','physical_hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/('latest_pitch_attempt.json'if original_pitches else'latest_subset_attempt.json'if selected else'latest_attempt.json')).write_text(json.dumps({'status':result['status'],'report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='cases'},ensure_ascii=False,indent=2));assert result['status']=='pass'
 finally:e.close()

if __name__=='__main__':main()
