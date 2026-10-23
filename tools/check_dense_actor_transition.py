"""Observe every LCD frame during 23-pose changes, including old visible VRAM.
Pixels may belong to the previous or final picture at scanout boundaries;
third, overwritten textures or palettes at a pixel are never accepted.
"""
import hashlib,json,struct,tempfile
from pathlib import Path
import numpy as np
from PIL import Image
from project_env import ROOT
from drive_opening import Emulator
from gba_fixture import fixture

def main():
 meta=json.loads((ROOT/'build/audio_manifest.json').read_text());census=json.loads((ROOT/'evidence/optimization_20261022/music/complete_score_census.json').read_text());t=next(t for t in meta['tracks']if t['name']=='INT03');peak=next(r for r in census['tracks']if r['name']=='INT03'and r['quality']==0)
 (ROOT/'build/dense_actor_transition_config.h').write_text('static const unsigned dense_music_id=%d,dense_music_seek=%d;\n'%(t['id'],max(0,peak['peak_source_position']-32768)))
 rom,elf,digest=fixture('tests/dense_actor_transition_gba.c','dense_actor_transition',{'video':'tests/native_palette_video.c'});out=ROOT/'evidence/optimization_20261022/dense_actor_transition'/digest[:12];out.mkdir(parents=True,exist_ok=True);e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf);rows=[]
 def debug():return struct.unpack('<4I',e.memory(e.symbols['dense_transition_debug'],16))
 def sound():return struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16))
 scratch=tempfile.TemporaryDirectory(prefix='ruina-lcd-transition-');current=Path(scratch.name)/'current.png'
 def shot():
  e.shot(current)
  with Image.open(current)as picture:return np.asarray(picture.convert('RGB')).copy()
 try:
  for _ in range(5000):
   if debug()[0]==1:break
   e.frames(1)
  else:raise AssertionError(('initial scene',debug()))
  e.frames(2);old=shot();Image.fromarray(old).save(out/'stage_1.png');initial_audio=sound()[0]-debug()[1];print('initial_audio_underruns',initial_audio,flush=True)
  for stage in range(2,8):
   frames=[];before_audio=sound()[0];last_audio=before_audio;audio_events=[]
   for n in range(3000):
    e.frames(1,1 if n<2 else 0);frames.append(shot());current_audio=sound()
    if current_audio[0]!=last_audio:audio_events.append({'frame':n,'new_underruns':current_audio[0]-last_audio,'last_serviced_queue':current_audio[2],'preparing':debug()[2]});last_audio=current_audio[0]
    if debug()[0]==stage:
     e.frames(2);new=shot();break
   else:raise AssertionError(('transition timeout',stage,debug()))
   bad=[]
   for i,pixels in enumerate(frames):
    unexpected=np.any(pixels!=old,axis=2)&np.any(pixels!=new,axis=2);count=int(unexpected.sum())
    if count:
     bad.append({'frame':i,'pixels':count})
     if len(bad)<=3:Image.fromarray(pixels).save(out/f'stage{stage}_unexpected_{i}.png')
   Image.fromarray(new).save(out/f'stage_{stage}.png');rows.append({'stage':stage,'hardware_frames_observed':len(frames),'unexpected_frames':bad,'audio_underruns':sound()[0]-before_audio,'audio_events':audio_events});old=new
   print(json.dumps(rows[-1]),flush=True)
  d=debug();audio=struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16));commit=struct.unpack('<3I',e.memory(e.symbols['video_native_commit_metrics'],12));deferred=list(struct.unpack('<2I',e.memory(e.symbols['video_native_texture_metrics'],8)))if'video_native_texture_metrics'in e.symbols else None
  checks={'no_pixels_from_overwritten_visible_textures':not any(r['unexpected_frames']for r in rows),'no_audio_underruns_after_priming':audio[0]==d[1],'all_native_commits_within_VBlank':commit[0]==0}
  result={'status':'pass'if all(checks.values())else'fail','production_rom_sha256':digest,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'scope':'controlled actual GBA, 23 simultaneous original poses changed six times, two original HUDs, dense original INT03 score and four original effects; every intermediate LCD frame observed','checks':checks,'initial_audio_underruns_after_priming':initial_audio,'audio_underruns_after_priming':audio[0]-d[1],'native_commit_metrics':commit,'deferred_texture_metrics':deferred,'transitions':rows,'physical_hardware':'not_run','commands':e.log};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':result['status'],'report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('commands','transitions')},ensure_ascii=False,indent=2));assert result['status']=='pass',checks
 finally:e.close();scratch.cleanup()
if __name__=='__main__':main()
