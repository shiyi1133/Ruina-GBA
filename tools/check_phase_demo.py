"""Actual new-game buttons, first battle, menu and ordinary-save cold loads."""
import argparse,hashlib,json,struct
from drive_opening import ROOT,Emulator
from check_save import opening
from save_observation import save_payload,check_load

def main():
 p=argparse.ArgumentParser();p.add_argument('--rom',type=str);p.add_argument('--elf',type=str);args=p.parse_args()
 from pathlib import Path
 rom=Path(args.rom).resolve()if args.rom else ROOT/'build/废都物语_GBA_开篇开发验证版.gba';elf=Path(args.elf).resolve()if args.elf else ROOT/'build/ruina_opening_dev.elf';digest=hashlib.sha256(rom.read_bytes()).hexdigest()
 out=ROOT/'evidence/phase_demo_20261021'/digest[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf);commands=[];seen_battle=False
 def phase():return struct.unpack('<i',e.memory(e.symbols['game']+8+41*4,4))[0]
 def position():return struct.unpack('<3i',e.memory(e.symbols['game']+29768,12))
 def until_world(target):
  nonlocal seen_battle
  for _ in range(250):
   d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,('halt',d)
   if d[5]==10710:
    if not seen_battle and d[15]in(1,2,6):
     e.key(0);mode=struct.unpack('<H',e.memory(0x04000000,2))[0]&7
     assert mode in(3,4),('battle incorrectly retained map-window hardware mode',mode,e.debug())
     assert int(e.command('lcdhash').split()[2])<38400,'unexpected black battle screen'
     e.shot(out/'first_battle.png');seen_battle=True
   if d[15]==4 and phase()==target:e.frames(60);return
   if d[15]in(1,2,6,7):
    if target==2 and d[15]==1:e.shot(out/'entrance_dialogue.png')
    e.key(1)
   else:e.frames(60)
  raise AssertionError(('world not reached',target,e.debug()))
 def investigate(eid):
  for _ in range(100):
   assert e.debug()[15]==4,e.debug()
   if e.debug()[11]==eid:e.key(1);return
   e.key(256)
  raise AssertionError(('point unavailable',eid))
 try:
  opening(e,1);e.frames(120);e.shot(out/'opening_cave.png')
  before=position();e.key(64);after=position();assert before!=after,(before,after)
  e.shot(out/'walking.png')
  # Original phase 1 exposes only the entrance. More points become available
  # after examining it; requiring two here would test an invented story state.
  e.key(256);first=e.debug()[11];assert first==1,first
  cursor=list(struct.unpack('<3H',e.memory(0x07000000+36*8,6)))
  visible=struct.unpack('<I',e.memory(e.symbols['cursor_visible'],4))[0]
  if visible:assert not cursor[0]&0x200 and cursor[2]&1023==800,cursor
  e.shot(out/'hardware_cursor.png')
  e.key(8);assert e.debug()[15]==2,e.debug();e.shot(out/'system_menu.png')
  e.key(2);until_world(1);assert position()==after
  investigate(1);until_world(2);e.shot(out/'entrance_examined.png')
  e.key(256);first=e.debug()[11];e.key(256);second=e.debug()[11]
  assert first and second and first!=second,(first,second)
  e.shot(out/'hardware_cursor_phase2.png')
  investigate(7);until_world(3);assert seen_battle
  actor=e.memory(e.symbols['game']+4068+196,196);hp,mp,xp=struct.unpack_from('<3i',actor,64)
  gold=struct.unpack('<i',e.memory(e.symbols['game']+29744,4))[0];assert xp==1 and gold==1,(hp,mp,xp,gold)
  e.shot(out/'first_victory.png')
  e.key(8);e.key(128);e.key(128);e.key(1);assert e.debug()[15]==1,e.debug()
  save=out/'phase_demo_test.sav';assert e.command('savecopy '+str(save)).startswith('SAVE ')
  version,payload=save_payload(save.read_bytes());assert version==5
  assert e.memory(e.symbols['game'],len(payload))==payload
  e.shot(out/'save_message.png');commands.append({'process':'new_game_and_save','commands':e.log.copy()})
 except Exception as ex:
  e.shot(out/'failed.png');(out/'failed_attempt.json').write_text(json.dumps({'status':'fail','error':repr(ex),'debug':list(e.debug()),'commands':e.log},ensure_ascii=False,indent=2));raise
 finally:e.close()
 loaded=Emulator(save,rom=rom,elf=elf)
 try:
  loaded.frames(30);loaded.key(1);loaded.key(128);loaded.key(1);loaded.frames(240)
  assert loaded.debug()[15]==4,loaded.debug();cold=check_load(loaded,payload)
  loaded.frames(2);loaded.shot(out/'after_cold_load.png');commands.append({'process':'new_save_cold_load','commands':loaded.log.copy()})
 finally:loaded.close()
 previous=ROOT/'evidence/save_cold_load/ordinary.sav';old_payload=save_payload(previous.read_bytes())[1];loaded=Emulator(previous,rom=rom,elf=elf)
 try:
  loaded.frames(30);loaded.key(1);loaded.key(128);loaded.key(1);loaded.frames(240)
  assert loaded.debug()[15]==4,loaded.debug();legacy=check_load(loaded,old_payload)
  commands.append({'process':'prior_demo_save_cold_load','commands':loaded.log.copy()})
 finally:loaded.close()
 assert hashlib.sha256(rom.read_bytes()).hexdigest()==digest
 report={'status':'pass','rom_sha256':digest,'kind':'actual production ROM, fresh new game, genuine emulated buttons and read-only observations','checks':['original origin and naming sequence','actual map movement','two map point selections using hardware OBJ cursor','open and close system menu','original entrance dialogue and event','first original battle and victory','ordinary in-game save and fresh-process cold load','prior-demo ordinary SAV cold load'],'walk_before':before,'walk_after':after,'cursor_selections':[first,second],'cursor_oam':cursor,'battle_after':{'hp':hp,'mp':mp,'xp':xp,'gold':gold,'story_phase':3},'new_save_load':cold,'previous_save_load':legacy,'full_playthrough':'not_run; player acceptance','hardware':'not_run','commands':commands}
 (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'report':str((out/'result.json').relative_to(ROOT)),'status':'pass'},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
