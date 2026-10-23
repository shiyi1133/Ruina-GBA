"""Read-only instruction/cycle samples during unchanged animation playback."""
import argparse,bisect,hashlib,json,struct,subprocess
from pathlib import Path
from drive_opening import ROOT,PREFIX,Emulator
from gba_fixture import fixture
def main():
 p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--start-frame',type=int,default=-1);p.add_argument('--windows',type=int,default=2);p.add_argument('--frames',type=int,default=120);args=p.parse_args();out=ROOT/'evidence/animation_smooth_20261023';generated=ROOT/'build/fixtures/animation_profile';generated.mkdir(parents=True,exist_ok=True)
 override=generated/'battle.c';override.write_text((ROOT/'runtime/rm2k/battle.c').read_text()+'\n'+(ROOT/'tests/battle_animation_target_setup.inc').read_text())
 rom,elf,production=fixture('tests/animation_profile_gba.c','animation_profile',{'battle':str(override)})
 symbols=[]
 for line in subprocess.check_output([PREFIX+'nm','-n','-S',str(elf)],text=True).splitlines():
  s=line.split()
  if len(s)==4 and s[2]in'tTwW'and int(s[1],16):symbols.append((int(s[0],16)&~1,int(s[1],16),s[3]))
 addresses=[r[0]for r in symbols];samples=[];e=Emulator(rom=rom,elf=elf)
 try:
  for _ in range(1000):
   if e.debug()[18]==1:break
   e.frames(4)
  else:raise AssertionError(e.debug())
  e.frames(2,1);e.frames(2)
  if args.start_frame>=0:
   for _ in range(6000):
    if struct.unpack('<2I',e.memory(e.symbols['animation_render_trace'],8))[1]>=args.start_frame:break
    assert e.debug()[18]!=2,'Animation ended before requested profiling point';e.frames(1)
   else:raise AssertionError('Requested original frame not reached')
  for phase in range(args.windows):
   path=out/f'profile_{args.label}_{phase}.txt';response=e.command(f'profile_cycles {args.frames} 0 {path}');totals={};unknown=0
   for line in path.read_text().splitlines():
    at,count,cycles=line.split();at=int(at,16);index=bisect.bisect_right(addresses,at)-1
    if index>=0 and at<symbols[index][0]+symbols[index][1]+16:name=symbols[index][2]
    else:name='unattributed'
    row=totals.setdefault(name,[0,0]);row[0]+=int(count);row[1]+=int(cycles)
   ordered=sorted(({'function':name,'instructions':r[0],'cycles':r[1]}for name,r in totals.items()),key=lambda r:r['cycles'],reverse=True)
   samples.append({'phase':phase,'trace':response,'functions':ordered});print(json.dumps({'phase':phase,'top':ordered[:18]},ensure_ascii=False,indent=2),flush=True)
  r={'production_ROM_sha256':production,'label':args.label,'scope':'Read-only PC and elapsed emulated CPU cycles over two 120-hardware-frame windows of full original animation 191, real MIDI and SFX, controlled battlers. PC bins have 16-byte precision.','samples':samples};(out/f'profile_{args.label}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
