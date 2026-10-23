"""Observe every completed original animation frame and wall-clock cadence."""
import argparse,hashlib,json,statistics,struct
from pathlib import Path
from drive_opening import ROOT,Emulator
import gba_fixture
def main():
 p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--project');p.add_argument('--full-frames',action='store_true');args=p.parse_args();project=Path(args.project).resolve()if args.project else ROOT;out=ROOT/'evidence/animation_smooth_20261023';stem='animation_cadence_'+args.label;generated=project/'build/fixtures'/stem;generated.mkdir(parents=True,exist_ok=True)
 override=generated/'battle.c';override.write_text((project/'runtime/rm2k/battle.c').read_text()+'\n'+(ROOT/'tests/battle_animation_target_setup.inc').read_text());old=gba_fixture.ROOT
 try:
  code=(ROOT/'tests/animation_profile_gba.c').read_text()
  if args.full_frames and'animation_playback_mode'in(project/'runtime/rm2k/animations.c').read_text():code=code.replace('animation_fixture_setup();','animation_fixture_setup();animation_playback_mode(1);')
  source=generated/'main.c';source.write_text(code);gba_fixture.ROOT=project;rom,elf,digest=gba_fixture.fixture(str(source),stem,{'battle':str(override)})
 finally:gba_fixture.ROOT=old
 e=Emulator(rom=rom,elf=elf);samples=[];last=0
 def clock():return int(e.command('timing').split()[3])
 try:
  for _ in range(1000):
   if e.debug()[18]==1:break
   e.frames(4)
  else:raise AssertionError(e.debug())
  started=clock();e.frames(1,1)
  for _ in range(6000):
   trace=struct.unpack('<16I',e.memory(e.symbols['animation_render_trace'],64))
   presented=struct.unpack('<4I',e.memory(e.symbols['animation_presented_trace'],16))if'animation_presented_trace'in e.symbols else(2*trace[2],trace[0],trace[1],clock())
   if not presented[0]&1 and presented[0]//2!=last:
    assert presented[0]//2==last+1,(last,presented);last=presented[0]//2;samples.append({'source_frame':presented[2],'hardware_frame':presented[3],'draw_ticks':trace[9],'restore_ticks':trace[12],'cells_ticks':trace[13],'LCD':e.command('lcdhash')})
   if e.debug()[18]==2:break
   e.frames(1)
  else:raise AssertionError(('animation stuck',e.debug()))
  elapsed=clock()-started;deltas=[b['hardware_frame']-a['hardware_frame']for a,b in zip(samples,samples[1:])];cache=list(struct.unpack('<8I',e.memory(e.symbols['animation_cache_debug'],32)))if'animation_cache_debug'in e.symbols else None
  result={'status':'pass','label':args.label,'production_ROM_sha256':digest,'fixture_ROM_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'source_frames_observed':len(samples),'source_frame_sequence':[r['source_frame']for r in samples],'seconds_including_preparation':elapsed*280896/16777216,'preparation_hardware_frames':samples[0]['hardware_frame']-started,'mean_hardware_frames_between_presentations':statistics.mean(deltas),'max_hardware_frames_between_presentations':max(deltas),'animation_cache':cache,'samples':samples,'scope':'Original 40-frame animation 191, controlled battlers and MIDI 1. Every completed frame observed by read-only per-hardware-frame sampling. Includes actual preparation and original waiting policy; no skipped animation frames, injected RAM or emulator speed changes.','physical_hardware':'not_run'}
  result['mode']='complete_frames'if args.full_frames else'original_time';result['scope']='Original animation 191, controlled battlers and MIDI 1. Completed presentations observed through a read-only seqlock and actual hardware clock. Whole time includes preparation. Original-time mode intentionally omits late transition frames; complete-frames mode preserves all 40. No running RAM writes or emulator speed changes.'
  assert result['source_frame_sequence']==sorted(set(result['source_frame_sequence'])) and result['source_frame_sequence'][-1]==39,result
  if args.full_frames:assert result['source_frame_sequence']==list(range(40)),result
  (out/f'cadence_{args.label}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='samples'},ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
