"""Whole animation wall time on hardware frames, with unchanged MIDI/SFX."""
import argparse,hashlib,json,struct
from pathlib import Path
from drive_opening import ROOT,Emulator
import gba_fixture

def main():
 p=argparse.ArgumentParser();p.add_argument('--project');p.add_argument('--label',required=True);p.add_argument('--full-frames',action='store_true');args=p.parse_args();project=Path(args.project).resolve()if args.project else ROOT;out=ROOT/'evidence/animation_optimization_20261023';stem='animation_playback_'+args.label;generated=project/'build/fixtures'/stem;generated.mkdir(parents=True,exist_ok=True)
 override=generated/'battle.c';override.write_text((project/'runtime/rm2k/battle.c').read_text()+'\n'+(ROOT/'tests/battle_animation_target_setup.inc').read_text())
 source=generated/'main.c';code=(ROOT/'tests/animation_playback_benchmark_gba.c').read_text();has_mode='animation_playback_mode'in(project/'runtime/rm2k/animations.c').read_text()
 if args.full_frames and has_mode:code=code.replace('animation_fixture_setup();','animation_fixture_setup();animation_playback_mode(1);')
 source.write_text(code);old=gba_fixture.ROOT
 try:
  gba_fixture.ROOT=project;rom,elf,production=gba_fixture.fixture(str(source),stem,{'battle':str(override)})
 finally:gba_fixture.ROOT=old
 e=Emulator(rom=rom,elf=elf);samples=[]
 try:
  for case,aid in enumerate((46,62,78,191)):
   for _ in range(3000):
    if e.debug()[18]==case+1:break
    assert e.debug()[0]!=0x4641554c,e.debug();e.frames(4)
   else:raise AssertionError(('before animation',case,e.debug()))
   e.frames(2,1);e.frames(2)
   for _ in range(10000):
    if e.debug()[18]==0x100+case:break
    assert e.debug()[0]!=0x4641554c,e.debug();e.frames(4)
   else:raise AssertionError(('animation incomplete',case,e.debug()))
   start,end,before,after,halt=struct.unpack('<5I',e.memory(e.symbols['animation_playback_samples']+case*20,20));assert not halt
   timing=list(struct.unpack('<8I',e.memory(e.symbols['animation_timing_debug'],32)))if'animation_timing_debug'in e.symbols else None
   samples.append({'animation':aid,'hardware_frames':end-start,'seconds':(end-start)*280896/16777216,'MIDI_underruns':after-before,'timing':timing});e.frames(2,1);e.frames(2)
  report={'status':'pass','label':args.label,'mode':'complete_frames'if args.full_frames or not has_mode else'original_time','production_ROM_sha256':production,'fixture_ROM_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'MIDI_track':1,'samples':samples,'total_seconds':sum(r['seconds']for r in samples),'scope':'Production animation_battle with original SFX and real MIDI. Hardware frame counter observed around full playback, including preparation; no user delay included. Controlled battlers/targets only. Not full gameplay FPS.'};(out/('playback_'+args.label+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
