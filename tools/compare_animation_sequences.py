"""Compare every original frame on the actual LCD with unmodified v0.7.3."""
import argparse,hashlib,json
from pathlib import Path
from drive_opening import ROOT,Emulator
from inspect_lcf import data_root,array
import gba_fixture
def main():
 p=argparse.ArgumentParser();p.add_argument('--baseline',required=True);p.add_argument('--all',action='store_true');p.add_argument('--label',required=True);p.add_argument('--ids');p.add_argument('--no-bake',action='store_true');p.add_argument('--no-fusion',action='store_true');args=p.parse_args();baseline=Path(args.baseline).resolve();out=ROOT/'evidence/animation_smooth_20261023';db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1];chosen=set(map(int,args.ids.split(',')))if args.ids else None;cases=[(aid,len(array(data.get(12,b''))))for aid,data in array(db[19])if(aid in chosen if chosen is not None else args.all or aid in(46,62,78,191))];header='static const int animation_sequences[][2]={'+','.join('{%d,%d}'%r for r in cases)+'};\n';roms=[]
 for project in(baseline,ROOT):
  stem='animation_sequence_'+args.label;generated=project/'build/fixtures'/stem;generated.mkdir(parents=True,exist_ok=True);(generated/'cases.h').write_text(header);main_source=generated/'main.c';main_source.write_text((ROOT/'tests/animation_sequence_comparison_gba.c').read_text().replace('animation_sequences.h','cases.h'));override=generated/'battle.c';override.write_text((project/'runtime/rm2k/battle.c').read_text()+'\n'+(ROOT/'tests/battle_animation_target_setup.inc').read_text());old=gba_fixture.ROOT
  overrides={'battle':str(override)}
  if project==ROOT and(args.no_bake or args.no_fusion):
   source=(project/'runtime/rm2k/animations.c').read_text()
   if args.no_bake:source=source.replace('if(scope){int baked','if(0&&scope){int baked')
   if args.no_fusion:source=source.replace('if(opaque<0&&count==1)','if(0&&opaque<0&&count==1)')
   controlled=generated/'animations.c';controlled.write_text(source);overrides['animations']=str(controlled)
  try:
   gba_fixture.ROOT=project;roms.append(gba_fixture.fixture(str(main_source),stem,overrides))
  finally:gba_fixture.ROOT=old
 old=Emulator(rom=roms[0][0],elf=roms[0][1]);new=Emulator(rom=roms[1][0],elf=roms[1][1]);rows=[]
 def until(e,stage):
  for _ in range(2000):
   if e.debug()[14]==stage:return
   assert e.debug()[0]!=0x4641554c,e.debug();e.frames(4)
  raise AssertionError(('stage timeout',stage,e.debug()))
 def advance(e):e.frames(2,1);e.frames(2)
 try:
  for i,(aid,n)in enumerate(cases):
   for frame in range(n):
    stage=0x10000000+(i<<12)+frame
    for e in(old,new):until(e,stage);e.frames(2);assert int.from_bytes(e.memory(0x04000000,2),'little')&7 in(3,4),'Fixture did not initialize an actual bitmap battle mode'
    a=old.command('lcdrgbhash');b=new.command('lcdrgbhash')
    if a!=b:
     old.shot(out/f'failure_{args.label}_{aid}_{frame}_baseline.png');new.shot(out/f'failure_{args.label}_{aid}_{frame}_candidate.png');raise AssertionError(('LCD mismatch',aid,frame,a,b))
    rows.append({'animation':aid,'frame':frame,'LCD':a})
    for e in(old,new):advance(e)
   for e in(old,new):until(e,0x20000000+i);e.frames(2)
   assert old.command('lcdrgbhash')==new.command('lcdrgbhash'),('clean restoration mismatch',aid)
   for e in(old,new):advance(e)
   if i%10==0:print('Compared',i+1,'animations;',len(rows),'original LCD frames',flush=True)
  result={'status':'pass','label':args.label,'baseline_ROM_sha256':roms[0][2],'production_ROM_sha256':roms[1][2],'animation_records':len(cases),'source_frames':len(rows),'all_LCD_pixels_identical':True,'clean_restoration_after_every_sequence':True,'scope':'Two separately linked controlled cartridges, unchanged production animation and rendering objects from v0.7.3 and this candidate. Every original frame and clean restoration compared by actual 64-bit LCD hash. Real buttons, paused logical clock between manual original frame ticks; audio remains live. This checks visual fidelity, not playback performance or complete gameplay.','physical_hardware':'not_run','frames':rows};(out/f'sequences_{args.label}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='frames'},ensure_ascii=False,indent=2))
 except Exception as error:
  (out/f'sequences_{args.label}_failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'frames_compared':len(rows),'baseline_ROM_sha256':roms[0][2],'production_ROM_sha256':roms[1][2]},indent=2));raise
 finally:old.close();new.close()
if __name__=='__main__':main()
