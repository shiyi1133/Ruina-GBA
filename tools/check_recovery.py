"""Real-input game-over/new-game reset and corrupt ordinary-SAV rejection."""
import json,struct,hashlib
from drive_opening import Emulator,ROOT
from check_save import opening

def main():
 out=ROOT/'evidence/recovery';out.mkdir(exist_ok=True);e=Emulator(ROOT/'evidence/chapter_progress/town_before_boss.sav')
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(240)
  from play_chapter import Chapter
  c=object.__new__(Chapter);c.e=e
  # Original dungeon entry disables saving. Start from the actual town save,
  # return to the cave and prepare the encounter with ordinary player actions.
  c.node(2);c.run_to_map();c.node(32);c.run_to_map()
  c.use_item(10);c.node(4,False);c.use_item(11)
  c.equip(519,0);c.equip(760,1);c.node(5)
  for _ in range(1200):
   d=e.debug()
   if _%100==0:print('defeat_check_step',_,d,flush=True)
   if d[1]==12420:break
   assert d[15]!=5,(d,'unexpected development fault')
   if d[15]==2 and d[19]==2:
    if d[16]!=2:e.key(128)
    else:e.key(1)
   elif d[15]in[1,2]:e.key(1)
   else:e.frames(60)
  else:raise AssertionError('defeat was not reached')
  e.frames(180);e.shot(out/'after_game_over.png');opening(e,1);game=e.symbols['game'];actor=e.memory(game+4068+196,196)
  assert struct.unpack_from('<i',actor,72)[0]==0 and actor[98]==1
  assert e.memory(game+3133+11,1)==b'\0';assert e.memory(game+2012+114,1)==b'\0'
  assert struct.unpack('<i',e.memory(game+8+41*4,4))[0]==1
  assert struct.unpack('<H',actor[88:90])[0]==515
  e.shot(out/'new_game_after_defeat.png');commands=e.log.copy()
 finally:e.close()
 bad=bytearray((ROOT/'evidence/save_cold_load/ordinary.sav').read_bytes());bad[128]^=128;p=out/'intentional_corruption.sav';p.write_bytes(bad);x=Emulator(p)
 try:
  x.frames(30);x.key(1);x.key(128);x.key(1);x.frames(240);assert x.debug()[15]==1,x.debug()
  text=x.memory(x.symbols['dialog'],8192).split(b'\0',1)[0].decode('gbk');assert '校验未通过'in text,text;x.shot(out/'corrupt_save_rejected.png');commands2=x.log.copy()
 finally:x.close()
 result={'status':'pass','rom_sha256':hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest(),'stock_defeat_reached':True,'new_game_after_defeat':{'level':1,'exp':0,'rope':0,'CP_flag':False,'initial_weapon':515,'story_phase':1},'corrupt_sav_rejected':True,'acceptance_input':'emulated keys','observations':'read only; deliberately corrupted copy used only for rejection test','ordinary_save_only':True,'commands_defeat_then_new_game':commands,'commands_corrupt_save':commands2}
 (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if not k.startswith('commands')},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
