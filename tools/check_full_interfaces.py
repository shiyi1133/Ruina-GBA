"""Real emulated buttons, separate controlled original-interface cartridge."""
import hashlib,json,struct
from drive_opening import Emulator,ROOT
from gba_fixture import fixture

def game_int(e,offset):return struct.unpack('<i',e.memory(e.symbols['game']+offset,4))[0]
def settle(e,want=(4,14),limit=120):
 for _ in range(limit):
  d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
  if d[15]in want:return d
  if d[15]in(1,2):e.key(1)
  else:e.frames(60)
 raise AssertionError(('settle',e.debug()))
def main():
 out=ROOT/'evidence/full_features/interfaces';out.mkdir(parents=True,exist_ok=True)
 rom,elf,digest=fixture('tests/full_features_gba.c','full_interfaces');checks=[]
 for option in range(5):
  e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav') if option==0 else Emulator(rom=rom,elf=elf)
  try:
   e.frames(60)
   if option==0:e.key(1);e.key(128);e.key(1)
   else:
    for _ in range(option):e.key(128)
    e.key(1)
   settle(e);e.key(0);actual_map=game_int(e,29768);assert actual_map==[23,17,20,14,15][option],(option,e.debug(),actual_map)
   e.shot(out/f'{option}_opened.png')
   initial=(game_int(e,29772),game_int(e,29776))
   if option<3:
    e.key(16 if option==1 else 64);settle(e);after=(game_int(e,29772),game_int(e,29776));e.shot(out/f'{option}_moved.png')
    assert after!=initial,(option,initial,after,e.debug())
    checks.append({'setup':'genuine opening SAV'if option==0 else'controlled source interface entry','interface':['walking','original handbook','original world map'][option],'opened_original_map':actual_map,'initial':initial,'after_buttons':after})
   else:
    # Original recipe event 6 is the first normal recipe, with original
    # materials/gold supplied only in this separate controlled cartridge.
    for _ in range(90):
     d=e.debug()
     if d[11]==6:break
     e.key(128)
    else:raise AssertionError('recipe not available')
    before=e.memory(e.symbols['game']+3133,933);money=game_int(e,29744)
    e.key(1);settle(e);after=e.memory(e.symbols['game']+3133,933)
    delta={str(i):after[i]-before[i]for i in range(933)if before[i]!=after[i]};assert delta,(option,e.debug())
    e.shot(out/f'{option}_crafted.png');checks.append({'interface':'weapon workshop'if option==3 else'armor workshop','original_recipe_event':6,'inventory_delta':delta,'gold_delta':game_int(e,29744)-money})
   checks[-1]['commands']=e.log
  except Exception:
   e.shot(out/f'{option}_stopped.png');(out/f'{option}_failed_commands.json').write_text(json.dumps(e.log));raise
  finally:e.close()
 report={'status':'pass','kind':'actual GBA emulator spot checks with controlled setup in a separate test ROM','release_rom_sha256':digest,'fixture_rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'release_rom_modified':False,'natural_campaign_playthrough':'user acceptance; not claimed by this fixture','checks':checks}
 (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='checks'},ensure_ascii=False))
if __name__=='__main__':main()
