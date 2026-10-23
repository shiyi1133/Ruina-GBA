"""Continue original events with real buttons; retain evidence on any stop.

No game-memory, register, function-call or emulator-state mutation is performed.
Read-only debug observations identify a selected node, as a player can visually.
"""
import json,struct,sys
from drive_opening import Emulator,ROOT
from check_save import opening
from check_first_battle import settle,phase

class Chapter:
 def __init__(self):
  self.e=Emulator();self.out=ROOT/'evidence/chapter_progress';self.out.mkdir(exist_ok=True);self.milestones=[];self.blocked_saves=[]
 def observe(self):
  d=self.e.debug()
  if d[15]==5 or d[0]==0x4641554c:raise RuntimeError(('unsupported',d))
  return d
 def party(self):
  game=self.e.symbols['game'];n=struct.unpack('<i',self.e.memory(game+29764,4))[0];return list(struct.unpack('<4i',self.e.memory(game+29748,16)))[:n]
 def run_to_map(self,limit=450,invite=None):
  invited_choices=set()
  for _ in range(limit):
   d=self.observe()
   if d[15]==2 and d[19]==1 and getattr(self,'last_battle_turn',None)!=(d[7],d[23]):
    self.last_battle_turn=(d[7],d[23]);raw=self.e.memory(self.e.symbols['units'],268*6);print('BATTLE',d[7],d[23],[list(struct.unpack_from('<4i',raw,i*268))for i in range(6)],flush=True)
   if d[15]in[4,12]:
    routing=struct.unpack('<2I',self.e.memory(self.e.symbols['world_trace']+16,8))if d[15]==4 else(0,0)
    if not any(routing):self.e.frames(24);return
   if d[15]==2 and d[19]==2 and d[7]in[5,10]:
    aid=d[13];actor=self.e.memory(self.e.symbols['game']+4068+aid*196,196);mp=struct.unpack('<i',self.e.memory(self.e.symbols['units']+self.party().index(aid)*268+12,4))[0];level=actor[98]
    wanted=(188 if aid in[1,6] and level>=2 and mp>=3 else 155 if aid==7 and mp>=6 else 183 if aid==7 and level>=2 and mp>=3 else 0)
    if wanted:
     self.battle_skill=wanted
     if d[16]!=1:self.e.key(128)
     else:self.e.key(1)
    else:self.e.key(1)
    continue
   if d[15]==6 and getattr(self,'battle_skill',0):
    if d[14]==self.battle_skill:self.e.key(1);self.battle_skill=0
    else:self.e.key(128)
    continue
   if d[15]in[1,2,6,7]:
    if d[15]==2 and invite is not None and d[6]==0 and d[7]==invite and d[17]>=3 and d[22]not in invited_choices:
     self.e.key(128);invited_choices.add(d[22])
    self.e.key(1)
   else:self.e.frames(60)
  raise RuntimeError(('UI_limit',self.e.debug()))
 def node(self,eid,activate=True):
  seen=set()
  for _ in range(130):
   d=self.observe();assert d[15]==4,d
   if d[11]==eid:
    # A selected marker is not the player's location. L+R really walks to
    # the point without activating it, so original position-based tools
    # such as the rope are used where the character actually stands.
    self.e.key(1 if activate else 768)
    # LCF path construction can precede the first published route count.
    self.e.frames(120)
    if not activate:self.run_to_map()
    return
   if d[11]in seen:raise RuntimeError(('node not currently available',eid,d[11]))
   seen.add(d[11]);self.e.key(256)
  raise RuntimeError('node navigation limit')
 def mark(self,name):
  self.e.shot(self.out/(name+'.png'));d=self.e.debug();gold=struct.unpack('<i',self.e.memory(self.e.symbols['game']+29744,4))[0];s={'name':name,'debug':list(d),'story_phase':phase(self.e),'party':self.party(),'gold':gold};self.milestones.append(s);print(json.dumps(s,ensure_ascii=False),flush=True)
 def save(self,name):
  allowed=struct.unpack('<i',self.e.memory(self.e.symbols['game']+29788,4))[0]
  if not allowed:
   self.blocked_saves.append({'requested':name,'map':self.e.debug()[9],'reason':'original event currently disables saving'})
   return None
  self.e.key(8);self.e.key(128);self.e.key(128);self.e.key(1);self.run_to_map();path=self.out/(name+'.sav');self.e.command('savecopy '+str(path));return path
 def use_item(self,item,target=0):
  self.e.key(8);self.e.key(128);self.e.key(1)
  for _ in range(100):
   d=self.observe()
   if d[15]==7:
    if d[18]==item:
     self.e.key(1);self.e.key(1)
     if item in[22,58]:
      for _ in range(target):self.e.key(128)
      self.e.key(1)
     self.run_to_map();return
    self.e.key(128)
   else:self.e.frames(60)
  raise RuntimeError(('inventory item unavailable',item))
 def explore(self):
  self.use_item(10);self.mark('09b_lantern_lit')
  self.node(16);self.run_to_map();self.mark('09c_goblin_defeated')
  self.node(13);self.run_to_map();self.mark('10_small_cave_searched')
  saved=self.save('party_exploring')
  if saved:assert saved.stat().st_size==32768,'ordinary save was not written'
  self.mark('11_exploration_saved' if saved else '11_original_cave_save_restriction');self.deeper()
 def item_count(self,item):return self.e.memory(self.e.symbols['game']+3133+item,1)[0]
 def buy_rope(self):
  before=self.item_count(11);self.node(1);bought=False
  for _ in range(150):
   d=self.observe();mode=d[15]
   if mode==4:break
   if mode==8:
    if bought:self.e.key(2)
    elif d[18]==11:self.e.key(1)
    else:self.e.key(128)
   elif mode==9:self.e.shot(self.out/'rope_purchase.png');self.e.key(1);bought=True
   elif mode==2:self.e.key(2 if bought else 1)
   elif mode==1:self.e.key(1)
   else:self.e.frames(60)
  assert bought and self.item_count(11)==before+1,'rope purchase did not change actual inventory'
 def buy_medicines(self,count=3):
  before=self.item_count(22);self.node(1);initial=True
  for _ in range(180):
   d=self.observe();mode=d[15]
   if mode==4:break
   if mode==2:
    if initial:self.e.key(128);self.e.key(1);initial=False
    elif self.item_count(22)<before+count:self.e.key(1)
    else:self.e.key(2)
   elif mode==1:self.e.key(1)
   else:self.e.frames(60)
  assert self.item_count(22)==before+count,'original scripted medicine purchase failed'
 def resupply(self):
  self.node(1);self.run_to_map();self.node(5);self.run_to_map();self.buy_medicines();self.use_item(22,1);self.use_item(22,2);self.mark('16a_medicine_resupply')
  self.node(2);self.run_to_map();self.node(32);self.run_to_map();self.save('resupplied_with_rope');self.pillar()
 def deeper(self):
  self.node(9);self.run_to_map();self.mark('12_pickaxe_obtained');assert self.item_count(12)==1
  self.node(2);self.run_to_map();self.mark('13_bats_defeated')
  self.node(17);self.run_to_map();self.mark('14_rockfall_passed');self.use_item(22,0);self.use_item(58,1);self.use_item(58,1);self.use_item(58,2);self.node(10);self.run_to_map();assert self.item_count(11)>0,'stone goblin encounter did not yield the original rope reward';self.mark('14b_stone_goblin_and_original_rewards');self.save('before_rope_purchase')
  self.node(1);self.run_to_map();self.node(5);self.run_to_map();assert self.e.debug()[9]==9;self.buy_rope();self.mark('15_rope_purchased');self.buy_medicines();self.use_item(22,1);self.use_item(22,2);self.mark('15b_original_medicine_used')
  saved=self.save('town_before_boss');assert saved and saved.stat().st_size==32768,'original town save failed'
  self.node(2);self.run_to_map();self.node(32);self.run_to_map();self.save('with_rope');self.mark('16_back_with_rope');self.pillar()
 def pillar(self):
  self.use_item(10);self.node(4,False);self.use_item(11);self.mark('17_rope_descent');self.save('before_dead_knight');self.finish_pillar()
 def equip(self,item,slot):
  self.e.key(8)
  for _ in range(3):self.e.key(128)
  self.e.key(1);self.e.key(1)
  for _ in range(slot):self.e.key(128)
  self.e.key(1)
  for _ in range(100):
   d=self.observe()
   if d[15]==10:
    if d[18]==item:self.e.key(1);self.run_to_map();break
    self.e.key(128)
   else:self.e.frames(60)
  actual=struct.unpack('<H',self.e.memory(self.e.symbols['game']+4068+196+88+slot*2,2))[0];assert actual==item,('actual equipment differs',actual,item)
 def finish_pillar(self):
  self.equip(519,0);self.equip(760,1);self.mark('17b_original_rewards_equipped')
  self.node(5);self.run_to_map(limit=600);assert phase(self.e)==15,'pillar scene did not finish';assert self.item_count(201)==1,'original title certificate reward missing';self.mark('18_first_checkpoint_cleared');self.save('checkpoint_cleared')
  self.node(21);self.run_to_map();assert self.e.debug()[9]==3 and self.e.debug()[15]in(4,12)and phase(self.e)==15,'checkpoint return not reached';self.mark('19_returned_to_town')
  saved=self.save('after_checkpoint_town');assert saved and saved.stat().st_size==32768
 def main(self):
  opening(self.e,1);self.mark('01_cave_entered');self.node(1);self.run_to_map();assert phase(self.e)==2
  self.node(7);self.run_to_map();assert phase(self.e)==3;self.mark('02_first_encounter_complete')
  self.node(1);self.run_to_map();self.mark('03_holm_town')
  self.node(8);self.run_to_map();self.mark('03b_first_home_visit')
  if self.e.debug()[9]==5:
   self.node(4);self.run_to_map();self.mark('03c_father_conversation')
   self.node(7);self.run_to_map();self.mark('03d_back_to_town')
  self.node(1);self.run_to_map();self.mark('04_tavern')
  self.node(3);self.run_to_map(invite=3);assert self.party()==[1,6],self.party();self.mark('05_nell_recruited')
  self.node(61);self.run_to_map(invite=61);assert self.party()==[1,6,7],self.party();self.mark('06_laban_recruited')
  saved=self.save('party_in_tavern');self.mark('07_party_ready_in_tavern' if saved is None else '07_party_saved')
  self.node(13);self.run_to_map();self.mark('08_town_with_party')
  self.node(32);self.run_to_map();self.mark('09_cave_with_party')
  self.save('reentered_cave');self.explore()
 def close(self):
  complete=bool(self.milestones and self.milestones[-1]['name']=='19_returned_to_town'and self.e.debug()[9]==3 and phase(self.e)==15)
  report={'status':'pass'if complete else'incomplete','scope':'knight opening, recruitment, original cave encounters, first CP and return to town; not full game','kind':'actual GBA button-driven campaign progress','milestones':self.milestones,'blocked_save_requests':self.blocked_saves,'commands':self.e.log,'chapter_complete':complete,'rom_sha256':__import__('hashlib').sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest(),'final_debug':list(self.e.debug())}
  (self.out/'progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));self.e.close()
def main():
 c=Chapter()
 try:
  if '--resume'in sys.argv:
   c.e.close();c.e=Emulator(c.out/('before_dead_knight.sav'if '--boss'in sys.argv else 'with_rope.sav'if '--pillar'in sys.argv else 'party_exploring.sav'if '--deeper'in sys.argv else 'reentered_cave.sav'));c.e.frames(30);c.e.key(1);c.e.key(128);c.e.key(1);c.e.frames(240);c.run_to_map();c.resupply()if '--resupply'in sys.argv else c.finish_pillar()if '--boss'in sys.argv else c.pillar()if '--pillar'in sys.argv else c.deeper()if '--deeper'in sys.argv else c.explore()
  else:c.main()
 except Exception as e:c.e.shot(c.out/'stopped.png');print('STOPPED',repr(e),flush=True);raise
 finally:c.close()
if __name__=='__main__':main()
