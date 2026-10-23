"""Actual GBA UI test with a separate, deliberately initialized fixture ROM.

No release-game bytes, emulated memory/registers or ordinary saves are edited.
This is capacity/UI verification, not natural progress to original troop 202.
"""
import hashlib,json,subprocess
from drive_opening import Emulator,ROOT,PREFIX

def main():
 out=ROOT/'evidence/mechanisms/battle_capacity';out.mkdir(exist_ok=True)
 fixture=ROOT/'build/fixtures/battle_capacity';fixture.mkdir(parents=True,exist_ok=True)
 production=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';before=hashlib.sha256(production.read_bytes()).hexdigest()
 flags=['-mcpu=arm7tdmi','-mthumb','-mthumb-interwork','-Os','-ffreestanding','-fno-builtin','-fdata-sections','-ffunction-sections','-g','-Isource','-Iruntime/rm2k','-Iplatform/gba','-Ibuild','-std=c99']
 obj=fixture/'main.o';subprocess.run([PREFIX+'gcc',*flags,'-c',str(ROOT/'tests/battle_capacity_gba.c'),'-o',str(obj)],cwd=ROOT,check=True)
 objects=[]
 for directory in ['source','runtime/rm2k','platform/gba']:
  objects += [ROOT/'build'/(p.stem+'.o')for p in sorted((ROOT/directory).glob('*.c'))if p.name!='game.c']
 objects += [ROOT/'build'/n for n in ['assets.o','source_menu_labels.o','midi_clock.o','start.o']]+[obj]
 elf=fixture/'capacity.elf';rom=fixture/'capacity.gba'
 subprocess.run([PREFIX+'gcc','-mcpu=arm7tdmi','-mthumb','-mthumb-interwork','-nostdlib','-Wl,-T,platform/gba/gba.ld',*map(str,objects),'-lgcc','-o',str(elf)],cwd=ROOT,check=True)
 subprocess.run([PREFIX+'objcopy','-O','binary',str(elf),str(rom)],check=True)
 b=bytearray(rom.read_bytes());b[4:192]=production.read_bytes()[4:192];rom.write_bytes(b)
 e=Emulator(rom=rom,elf=elf)
 try:
  for _ in range(30):
   e.frames(60);d=e.debug();assert d[0]!=0x4641554c,d
   if d[15]==2 and d[19]==1:break
   if d[15]==1:e.key(1)
  else:raise AssertionError(('battle menu not reached',e.debug()))
  e.key(1);assert e.debug()[19]==2,e.debug();e.key(1)
  d=e.debug();assert d[15]==2 and d[19]==3 and d[17]==10,d
  e.shot(out/'ten_enemy_targets.png')
  for _ in range(9):e.key(128)
  d=e.debug();assert d[16]==9 and d[17]==10,d;e.shot(out/'tenth_enemy_selected.png')
  e.key(1);assert e.debug()[13]==6 and e.debug()[19]==2,e.debug()
  assert hashlib.sha256(production.read_bytes()).hexdigest()==before
  report={'status':'pass','kind':'actual GBA emulator running a separate controlled UI fixture','original_troop':202,'enemy_targets':10,'four_party_members':True,'tenth_enemy_selectable':True,'release_rom_modified':False,'release_rom_sha256':before,'fixture_rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'natural_campaign_playthrough':'not_run','emulator_states_used':False,'memory_observations':'read only','commands':e.log}
  (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
