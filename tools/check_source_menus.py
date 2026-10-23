"""Actual-button checks for original title/cooking/alchemy events on GBA.
Uses an ordinary campaign save. Does not inject items/SP, call game functions,
write game memory, load emulator states or change the delivered original data.
"""
import argparse,collections,hashlib,json,struct,sys
from pathlib import Path
from drive_opening import Emulator,ROOT
from save_observation import check_load,save_payload
class Run:
 def __init__(self,save,rom=None,elf=None,out=None):
  self.rom=rom or ROOT/'build/废都物语_GBA_开篇开发验证版.gba';self.elf=elf or ROOT/'build/ruina_opening_dev.elf'
  self.e=Emulator(save,rom=self.rom,elf=self.elf);self.out=out or ROOT/'evidence/refactor/menus';self.out.mkdir(parents=True,exist_ok=True);self.checks=[]
 def debug(self):
  d=self.e.debug()
  assert d[0]!=0x4641554c and d[15]!=5,('unsupported',d)
  return d
 def var(self,n):return struct.unpack('<i',self.e.memory(self.e.symbols['game']+8+n*4,4))[0]
 def inventory(self):return self.e.memory(self.e.symbols['game']+3133,933)
 def gold(self):return struct.unpack('<i',self.e.memory(self.e.symbols['game']+29744,4))[0]
 def actor(self,a):return self.e.memory(self.e.symbols['game']+4068+a*196,196)
 def settle(self,modes=(4,14),choice=0):
  for _ in range(400):
   d=self.debug()
   if d[15]in modes:
    # Point selection starts an actual walk, and the world remains mode 4
    # until arrival. Do not mistake an in-progress route for the next menu.
    routing=struct.unpack('<2I',self.e.memory(self.e.symbols['world_trace']+16,8))if d[15]==4 else (0,0)
    if not any(routing):return d
   if d[15]==12:self.e.key(1)
   elif d[15]==2:self.choose(choice)
   elif d[15]in(1,6):self.e.key(1)
   else:self.e.frames(60)
  raise AssertionError(('settle',self.e.debug()))
 def choose(self,index):
  assert self.debug()[15]==2,self.e.debug()
  for _ in range(index):self.e.key(128)
  self.e.key(1)
 def node(self,event,activate=True):
  mode=self.debug()[15];assert mode in(4,14),self.e.debug();seen=set()
  for _ in range(520):
   d=self.debug()
   if d[11]==event:
    if activate:self.e.key(1)
    return
   assert d[11]not in seen,('event unavailable',event,sorted(seen));seen.add(d[11]);self.e.key(256 if mode==4 else 128)
  raise AssertionError('selection limit')
 def capture(self,name):self.e.shot(self.out/(name+'.png'))
 def skill(self,id):
  self.e.key(8)
  for _ in range(4):self.e.key(128)
  self.e.key(1);self.choose(1)
  assert self.debug()[15]==15,self.e.debug()
  for _ in range(430):
   if self.debug()[14]==id:self.e.key(1);return self.settle()
   self.e.key(128)
  raise AssertionError(('skill unavailable',id))
 def exit(self):self.e.key(2);return self.settle()
 def run(self):
  self.e.frames(30);self.e.key(1);self.e.key(128);self.e.key(1);self.e.frames(180);self.settle()
  assert self.var(41)==15 and self.inventory()[201]==1
  self.node(21);self.settle();assert self.debug()[9]==3
  # Original title acquisition: Knight, cost 2 SP plus one certificate.
  oldsp=self.var(26);self.node(9);self.settle();self.capture('01_title_choices')
  before=self.actor(1);self.node(7);self.settle();after=self.actor(1)
  assert self.var(26)==oldsp-2 and self.inventory()[201]==0
  assert self.var(182)==1 and self.var(210)==2
  assert after[32:64].split(b'\0',1)[0].decode('gbk').startswith('骑士')
  assert after[100:164]!=before[100:164],'original title skills were not learned'
  self.capture('02_title_acquired')
  sp=self.var(26);self.node(7);self.settle();assert self.var(26)==sp and self.var(182)==1
  self.checks.append({'name':'title acquisition and insufficient-SP retry','SP_before':oldsp,'SP_after':sp,'certificates_consumed':1,'title_level':self.var(182),'skills_changed':True})
  self.exit();assert self.debug()[9]==3
  # Original alchemy: 1 Turnip Moss -> 1 healing medicine. Cancel is inert.
  self.skill(10);assert self.debug()[9]==19;self.capture('03_alchemy_choices')
  before=self.inventory();self.node(7);self.settle(choice=1);assert self.inventory()==before
  self.node(7);self.settle();after=self.inventory()
  assert after[302]==before[302]-1 and after[22]==before[22]+1
  self.capture('04_medicine_created')
  self.checks.append({'name':'alchemy cancel and successful production','ingredient':302,'consumed':1,'product':22,'produced':1})
  self.exit();assert self.debug()[9]==3
  self.e.key(8);self.e.key(1);self.capture('05_status_with_title');self.e.key(2);self.settle()
  logs=self.cold_check('after_title_and_alchemy');self.settle()
  # A separate, genuine pre-exploration save still has original starting bread.
  # The ingredient merchant is correctly locked until phase 20: do not bypass
  # that condition or add ingredients merely to make this test run.
  logs+=self.e.log;self.e.close();early=ROOT/'history/legacy_reentered_cave_v2.sav';self.e=Emulator(early,rom=self.rom,elf=self.elf)
  self.e.frames(30);self.e.key(1);self.e.key(128);self.e.key(1);self.e.frames(180);self.settle()
  assert self.var(41)==9 and self.inventory()[58]>0
  self.checks.append({'name':'cooking starting point','ordinary_save':str(early.relative_to(ROOT)),'sha256':hashlib.sha256(early.read_bytes()).hexdigest(),'phase':9})
  # Original cooking recipe: bread alone -> dry bread (fixed original recipe).
  self.skill(8);assert self.debug()[9]==13;self.capture('05_cooking_ingredients')
  before=self.inventory();money=self.gold();self.node(9);self.settle();self.node(1);self.settle()
  after=self.inventory();product=self.var(170)
  want=collections.Counter({58:-1});want[product]+=1
  actual={i:after[i]-before[i]for i in range(933)if after[i]!=before[i]}
  assert product==151 and actual=={i:n for i,n in want.items()if n},(actual,want,product)
  assert self.gold()==money
  self.capture('06_original_dish_created');self.checks.append({'name':'original bread -> dry bread recipe','ingredients':[58],'product':product,'inventory_delta':actual,'extra_gold_deducted':0})
  self.exit();assert self.debug()[9]==23
  self.node(1);self.settle();assert self.debug()[9]==3
  self.node(5);self.settle();assert self.debug()[9]==9
  # Commission crafting is not offered at this original story phase. The
  # dedicated later-game workshop gameplay is intentionally not counted here.
  self.checks.append({'name':'weapon/armor workshop gameplay','status':'not_run','reason':'original commission/skill unlock requirements have not been reached in these chapter fixtures'})
  logs+=self.cold_check('after_cooking_and_workshops')
  return logs+self.e.log
 def cold_check(self,name):
  # Ordinary in-game save, then a fresh process; exact Game payload comparison.
  self.e.key(8);self.e.key(128);self.e.key(128);self.e.key(1)
  for _ in range(30):
   if self.debug()[15]==1:break
   self.e.frames(30)
  saved=self.out/(name+'.sav');reply=self.e.command('savecopy '+str(saved));assert reply=='SAVE 32768',('ordinary SAV copy failed',reply,str(saved));b=saved.read_bytes();magic,version,size,source,crc=struct.unpack_from('<5I',b)
  assert magic==0x41554952 and version==5 and source==0x589a0adb
  version,payload=save_payload(b);size=len(payload);assert self.e.memory(self.e.symbols['game'],size)==payload
  logs=self.e.log.copy();self.e.close();self.e=Emulator(saved,rom=self.rom,elf=self.elf)
  self.e.frames(30);self.e.key(1);self.e.key(128);self.e.key(1);self.e.frames(180);state_check=check_load(self.e,payload)
  self.capture(name+'_cold_load');self.checks.append({'name':name+' ordinary save cold-load','save_message_paused_game_byte_match':True,'bytes':size,'load_observations':state_check})
  return logs
def main():
 p=argparse.ArgumentParser();p.add_argument('save',nargs='?');p.add_argument('--rom');p.add_argument('--elf');p.add_argument('--out');args=p.parse_args()
 save=Path(args.save)if args.save else ROOT/'history/legacy_checkpoint_v2.sav'
 r=Run(save,Path(args.rom).resolve()if args.rom else None,Path(args.elf).resolve()if args.elf else None,Path(args.out).resolve()if args.out else None)
 try:
  commands=r.run();report={'status':'pass','kind':'actual GBA emulator, original campaign ordinary SAV, buttons only','rom_sha256':hashlib.sha256(r.rom.read_bytes()).hexdigest(),'input_save_sha256':hashlib.sha256(save.read_bytes()).hexdigest(),'input_save_version':struct.unpack_from('<I',save.read_bytes(),4)[0],'checks':r.checks,'commands':commands,'all_original_optional_systems':'not_complete','hardware':'not_run'}
  (r.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2))
 except Exception:
  r.capture('stopped');(r.out/'failed_commands.json').write_text(json.dumps(r.e.log));raise
 finally:
  if r.e.proc.poll()is None:r.e.close()
if __name__=='__main__':main()
