"""Spot-check a frozen playable demo, separate from ongoing audio experiments."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator
from check_save import opening

def main():
 frozen=ROOT/'history/pre_native_playback_20261021';rom=frozen/'废都物语_GBA_开篇开发验证版.gba';elf=frozen/'ruina_opening_dev.elf'
 out=ROOT/'evidence/demo_20261021';out.mkdir(exist_ok=True);e=Emulator(rom=rom,elf=elf);battle=False
 def phase():return struct.unpack('<i',e.memory(e.symbols['game']+8+41*4,4))[0]
 def run_to_phase(target):
  nonlocal battle
  for _ in range(250):
   d=e.debug()
   assert d[15]!=5 and d[0]!=0x4641554c,('halt',d)
   if d[5]==10710:
    if not battle:e.shot(out/'first_battle.png')
    battle=True
   if d[15]==4 and phase()==target:
    e.frames(60);return
   if d[15]in (1,2,6,7):e.key(1)
   else:e.frames(60)
  raise AssertionError(('phase not reached',target,e.debug()))
 def investigate(eid):
  for _ in range(100):
   assert e.debug()[15]==4,e.debug()
   if e.debug()[11]==eid:e.key(1);return
   e.key(256)
  raise AssertionError(('point unavailable',eid))
 try:
  opening(e,1);e.frames(120);e.shot(out/'opening_cave.png')
  start=struct.unpack('<3i',e.memory(e.symbols['game']+29768,12));e.key(64)
  after=struct.unpack('<3i',e.memory(e.symbols['game']+29768,12));assert start!=after,(start,after);e.shot(out/'walking.png')
  investigate(1);run_to_phase(2);e.shot(out/'entrance_examined.png')
  investigate(7);run_to_phase(3);assert battle;e.shot(out/'first_victory.png')
  actor=e.memory(e.symbols['game']+4068+196,196);hp,mp,xp=struct.unpack_from('<3i',actor,64);gold=struct.unpack('<i',e.memory(e.symbols['game']+29744,4))[0];assert xp==1 and gold==1,(hp,mp,xp,gold)
  report={'status':'pass','rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'kind':'actual new game, normal emulator buttons and read-only observations','checks':['new game opening and original origin/name selection','real movement on the original map','original entrance event','first original battle and victory event'],'walk_before':start,'walk_after':after,'hp_after':hp,'mp_after':mp,'xp_after':xp,'gold_after':gold,'story_phase_after':phase(),'full_game_playthrough':'not_run, user acceptance','performance_optimization':'not_complete','commands':e.log}
  (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2),flush=True)
 finally:e.close()

if __name__=='__main__':main()
