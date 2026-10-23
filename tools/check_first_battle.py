"""Actual-button smoke test: original entrance, first encounter, post-battle event.

This verifies that the native flow runs. It is not a full original-engine
comparison or chapter acceptance test.
"""
import argparse,json,struct,sys
from pathlib import Path
from drive_opening import Emulator,ROOT
from check_save import opening

def phase(e):return struct.unpack('<i',e.memory(e.symbols['game']+8+41*4,4))[0]
def settle(e,wanted=4,wanted_phase=None):
 for _ in range(100):
  d=e.debug()
  if d[15]==5 or d[0]==0x4641554c:raise AssertionError(('halt',d))
  if d[15]==wanted:
   routing=struct.unpack('<2I',e.memory(e.symbols['world_trace']+16,8))if wanted==4 else(0,0)
   if not any(routing)and(wanted_phase is None or phase(e)==wanted_phase):return
  if d[15]in(1,2):e.key(1)
  else:e.frames(60)
 raise AssertionError('UI did not settle')
def main():
 p=argparse.ArgumentParser();p.add_argument('origin',type=int,nargs='?',default=1);p.add_argument('--rom');p.add_argument('--elf');p.add_argument('--auto',action='store_true');p.add_argument('--town',action='store_true');args=p.parse_args();origin=args.origin
 rom=Path(args.rom).resolve()if args.rom else ROOT/'build/废都物语_GBA_开篇开发验证版.gba';elf=Path(args.elf).resolve()if args.elf else ROOT/'build/ruina_opening_dev.elf'
 out=ROOT/'evidence'/(f"first_battle_origin_{origin}"+('_auto'if args.auto else ''));out=out/(__import__('hashlib').sha256(rom.read_bytes()).hexdigest()[:12])if args.rom else out;out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf);opening(e,origin);e.frames(60);e.key(1);settle(e,wanted_phase=2);assert phase(e)==2
 e.shot(out/'entrance_investigated.png')
 for _ in range(100):
  if e.debug()[11]==7:break
  e.key(256)
 else:raise AssertionError(('encounter point unavailable',e.debug()))
 e.key(1)
 used_magic=set();seen_battle=False
 for _ in range(250):
  d=e.debug()
  if d[15]==5 or d[0]==0x4641554c:raise AssertionError(('halt',d))
  if d[5]==10710 and d[15]in(1,2,6)and not seen_battle:
   e.key(0);mode=struct.unpack('<H',e.memory(0x04000000,2))[0]&7
   assert mode in(3,4),('battle incorrectly retained map-window hardware mode',mode,e.debug())
   assert int(e.command('lcdhash').split()[2])<38400,'unexpected black battle screen'
   e.shot(out/'encounter.png');seen_battle=True
  if d[15]==4 and phase(e)==3:break
  if d[15]==2:
   if '--auto'in sys.argv and d[19]==1 and d[5]==10710:e.key(128)
   elif origin==3 and d[5]==10710 and d[17]==4 and d[22]not in used_magic:
    e.key(128);used_magic.add(d[22])
   e.key(1)
  elif d[15]in(1,6):e.key(1)
  else:e.frames(60)
 else:raise AssertionError('first encounter did not complete')
 e.frames(60);e.shot(out/'after_first_victory.png')
 game=e.symbols['game'];actor=e.memory(game+4068+origin*196,196)
 hp,mp,xp=struct.unpack_from('<iii',actor,64);level=actor[98]
 gold=struct.unpack('<i',e.memory(game+29744,4))[0]
 assert xp==1 and level==1 and gold==1,(hp,mp,xp,level,gold)
 assert seen_battle
 report={'test':'native original opening first encounter flow','origin':origin,'status':'pass','engine':'actual GBA emulator','input':'buttons','memory':'read-only observations','battle_troop':1,'enemy':1,'hp_after':hp,'mp_after':mp,'exp_after':xp,'level_after':level,'gold_after':gold,'mage_used_original_skill_201':bool(used_magic)or(origin==3 and '--auto'in sys.argv and mp==8),'battle_mode':'automatic'if '--auto'in sys.argv else 'manual','rom_sha256':__import__('hashlib').sha256(rom.read_bytes()).hexdigest(),'postbattle_original_story_phase':phase(e),'full_chapter':'not_run','original_engine_comparison':'not_run','commands':e.log}
 if '--town' in sys.argv:
  # Direct movement deliberately cancels a remote target since v0.6.1.
  # Select the entrance explicitly instead of assuming a down key selects it.
  for _ in range(100):
   if e.debug()[11]==1:break
   e.key(256)
  else:raise AssertionError(('entrance point unavailable',e.debug()))
  e.key(1)
  for step in range(250):
   d=e.debug()
   if d[15]==5 or d[0]==0x4641554c:
    e.shot(out/'town_halt.png');report['town_attempt']={'status':'unsupported','debug':list(d)};break
   if d[15]==4 and d[9]==3:
    e.frames(60);e.shot(out/'holm_town.png');report['town_attempt']={'status':'reached','debug':list(d)};break
   if d[15]in(1,2):e.key(1)
   else:e.frames(60)
  else:report['town_attempt']={'status':'iteration_limit','debug':list(e.debug())}
 e.close();(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
