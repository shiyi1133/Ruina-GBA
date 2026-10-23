"""Real LCD checks for mutable status, shared modals and VRAM ownership."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator
from gba_fixture import fixture

def main():
 out=ROOT/'evidence/animation_smooth_20261023';generated=ROOT/'build/fixtures/animation_cache_reuse';generated.mkdir(parents=True,exist_ok=True)
 source=(ROOT/'runtime/rm2k/battle.c').read_text()+'\n'+(ROOT/'tests/battle_animation_target_setup.inc').read_text()+'''
void animation_fixture_cache_change(int stage){
 if(stage==2){units[0].hp=711;units[1].mp=83;turn=7;focus=2;}
 if(stage==3){units[4].hp=345;units[4].mp=9;}
 if(stage==4)units[4].hp=0;
 if(stage==5)units[5].hidden=1;
 if(stage==6)units[6].eid=2;
 if(stage==7){balanced_animation_background_forget();balanced_battle_cache_store();}
 if(stage==8)balanced_save_workspace();
 if(stage==9){units[4].hp=222;units[5].hidden=0;}
 if(stage==10){turn=9;focus=0;}
}
'''
 override=generated/'battle.c';override.write_text(source);rom,elf,digest=fixture('tests/animation_cache_reuse_gba.c','animation_cache_reuse',{'battle':str(override)});e=Emulator(rom=rom,elf=elf);checks=[]
 try:
  for stage in range(1,12):
   expected=None
   for phase in range(1,4):
    for _ in range(2500):
     d=e.debug();assert d[0]!=0x4641554c,d
     if d[18]==stage and d[20]==phase:break
     e.frames(2)
    else:raise AssertionError((stage,phase,e.debug()))
    e.frames(2);lcd=e.command('lcdhash');cache=list(struct.unpack('<4I',e.memory(e.symbols['animation_cache_reuse_debug'],16)))
    if expected is None:expected=lcd
    assert lcd==expected,(stage,phase,lcd,expected)
    checks.append({'stage':stage,'phase':phase,'LCD':lcd,'reuse_counters':cache});e.frames(2,1);e.frames(2)
  assert cache[0]>=1 and cache[1]>=3 and cache[2]>=6 and cache[3]>=10,cache
  r={'status':'pass','production_ROM_sha256':digest,'fixture_ROM_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'LCD_checks':len(checks),'checks':checks,'scope':'Clean battle LCD compared with whole cached restoration and shared modal restoration after HP/MP, focus/turn, enemy death/hiding/transform, raw modal overwrite, save workspace epoch and revival changes. No running RAM injection.','physical_hardware':'not_run'};(out/'cache_reuse.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in r.items()if k!='checks'},ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
