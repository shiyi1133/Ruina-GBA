"""Real legacy campaign battle menus, nested cancellation and resources."""
import hashlib,json,struct,time,sys
from drive_opening import ROOT,Emulator
from response_meter import ResponseMeter

def main():
 rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=hashlib.sha256(rom.read_bytes()).hexdigest();save=ROOT/'tests/fixtures/before_dead_knight.sav';saved_hash=hashlib.sha256(save.read_bytes()).hexdigest()
 reference='--reference'in sys.argv;reference_rom=None;reference_elf=None
 if reference:
  from gba_fixture import fixture
  generated=ROOT/'build/battle_menu_reference';generated.mkdir(exist_ok=True);overrides={}
  for name,path in [('dialog','platform/gba/dialog.c'),('battle','runtime/rm2k/battle.c'),('inventory','runtime/rm2k/inventory.c')]:
   text=(ROOT/path).read_text()
   if name=='dialog':
    a=text.index('void balanced_menu_background(');b=text.index('int choices_selected(',a)
    text=text[:a]+'void balanced_menu_background(int x,int y,int width,int height){draw_scene();}\n'+text[b:]
   text=text.replace('int full=first||scene_stamp!=stamp','int full=1').replace('int full=first||stamp!=scene_stamp','int full=1')
   if name=='inventory':text=text.replace('if(full||complex)inventory_full','if(1)inventory_full')
   target=generated/(name+'.c');target.write_text(text);overrides[name]=str(target)
  reference_rom,reference_elf,_=fixture('source/game.c','battle_menu_full_reference',overrides)
 out=ROOT/'evidence/balanced_optimization_20261023'/digest[:12]/('battle_menu_navigation_full_reference'if reference else'battle_menu_navigation');out.mkdir(parents=True,exist_ok=True);e=Emulator(save,reference_rom,reference_elf);meter=ResponseMeter(e);checks=[]
 def mode(kind,sub=None):
  d=e.debug();assert d[15]==kind and(sub is None or d[19]==sub),d
 def resources():
  raw=e.memory(e.symbols['units'],268*14);active=struct.unpack('<i',e.memory(e.symbols['total'],4))[0]
  return {'unit_HP_MP':[struct.unpack_from('<2i',raw,i*268+8)for i in range(active)],'inventory':e.memory(e.symbols['game']+3133,933).hex(),'item_usage':e.memory(e.symbols['game']+30082,933).hex(),'gold':e.memory(e.symbols['game']+29744,4).hex(),'turn':e.memory(e.symbols['turn'],4).hex(),'rng':e.memory(e.symbols['game']+4,4).hex()}
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(240);mode(4)
  for _ in range(100):
   if e.debug()[11]==5:break
   e.key(256)
  else:raise AssertionError('original dead-knight point not available')
  e.key(1)
  for _ in range(500):
   d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
   if d[15]==2 and d[19]==1:break
   if d[15]in(1,2,6,7):e.key(1)
   else:e.frames(60)
  else:raise AssertionError(('original boss battle did not begin',e.debug()))
  initial=resources();audio_start=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];e.shot(out/'battle_root.png')
  meter.action('enter_actor_commands',1);mode(2,2)
  for _ in range(6):meter.action('actor_commands_down',128);meter.action('actor_commands_up',64)
  meter.action('cancel_actor_to_battle_root',2);mode(2,1);assert resources()==initial
  checks.append('B from first actor commands returns to battle mode; resources and RNG unchanged')
  e.key(1);e.key(128);e.key(128);e.key(1) # First actor defends provisionally; companion has three real learned skills.
  e.key(128);meter.action('enter_skill_list',1);mode(6,5);count=e.debug()[17];assert count>=2,('need a real multi-skill list',e.debug())
  for _ in range(6):meter.action('skill_list_down',128);meter.action('skill_list_up',64)
  chosen=e.debug()[14];e.shot(out/'skills.png')
  e.key(1);mode(6,5);assert e.debug()[14]==chosen # Original companion lacks MP here; unusable selection must stay in place.
  meter.action('cancel_skills_to_actor',2);mode(2,2);assert e.debug()[16]==1
  meter.action('cancel_actor_to_battle_root',2);mode(2,1);assert resources()==initial
  e.key(1);e.key(128);e.key(128);e.key(1)
  for _ in range(3):e.key(128)
  meter.action('enter_item_list',1);mode(7);assert e.debug()[17]>=2,e.debug()
  for _ in range(6):meter.action('item_list_down',128);meter.action('item_list_up',64)
  for _ in range(200):
   if e.debug()[18]==22:break
   e.key(128)
  else:raise AssertionError('original healing medicine missing')
  e.shot(out/'items.png');meter.action('choose_item_target',1);mode(2,4)
  meter.action('target_list_down',128);meter.action('target_list_up',64)
  e.shot(out/'item_targets.png');meter.action('cancel_target_to_items',2);mode(7);assert e.debug()[18]==22
  meter.action('cancel_items_to_actor',2);mode(2,2);assert e.debug()[16]==3
  meter.action('cancel_actor_to_battle_root',2);mode(2,1);assert resources()==initial
  checks+=['B from item targets returns to the same item','B from skills/items retains parent command cursor','All cancellations preserve HP, MP, items, usage, gold, turn and RNG','Unusable original skill stays in list without consuming resources']
  held={}
  if not reference:
   e.key(1);expected=set()
   for _ in range(4):
    expected.add(e.command('lcdhash').split()[1]);e.key(128)
   trace=[]
   for _ in range(90):
    e.frames(1,128);_,h,black=e.command('lcdhash').split();trace.append(h);assert int(black)!=38400 and h in expected,(h,expected)
   e.key(0);changes=sum(a!=b for a,b in zip(trace,trace[1:]));assert changes>=5,changes
   held={'hardware_frames':90,'complete_cursor_changes':changes,'valid_complete_LCD_states':len(expected),'intermediate_or_black_frames':0}
   e.key(2);mode(2,1);assert resources()==initial
  assert not any(r['black_LCD_frames']or r['intermediate_LCD_frames']for r in meter.samples)
  report={'status':'pass','production_ROM_sha256':digest,'scope':'Original campaign ordinary SAV, real first-CP boss; actual key presses and read-only observations, no injected skills/items/stats.','controlled_full_redraw_reference':reference,'held_repeat':held,'input_SAV_sha256':saved_hash,'LCD_states':[r['trace'][-1]['LCD_hash']for r in meter.samples],'music_underruns':struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0]-audio_start,'checks':checks,'skill_choices':count,'summary':meter.summary(),'samples':meter.samples,'commands':e.log,'physical_hardware':'not_run','full_campaign':'not_run'}
  assert not report['music_underruns'],report['music_underruns']
  assert hashlib.sha256(save.read_bytes()).hexdigest()==saved_hash
  (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k not in('samples','commands')},ensure_ascii=False,indent=2))
 except Exception as err:
  e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(err),'debug':e.debug(),'samples':meter.samples,'commands':e.log},ensure_ascii=False,indent=2));raise
 finally:e.close()
if __name__=='__main__':main()
