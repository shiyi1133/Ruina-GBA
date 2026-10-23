"""Read CPU SP on genuine ordinary-save menu inputs; no sentinels or writes."""
import hashlib,json,re,struct
from project_env import ROOT
from drive_opening import Emulator

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/stack'/digest[:12];out.mkdir(exist_ok=True);e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav');rows=[];end=None
 def sample(label,key=0):
  r=e.command('stack 120 %x'%key);modes={int(a,16):{'minimum_SP':int(b,16),'at_PC':int(c,16),'instructions_observed':int(d)}for a,b,c,d in re.findall(r'([0-9a-f]{2}):([0-9a-f]{8}):([0-9a-f]{8}):(\d+)',r)};row={'scene':label,'modes':modes,'SYS_margin_above_fast_code_data':modes[31]['minimum_SP']-end};rows.append(row);print(label,row,flush=True);e.frames(2);e.shot(out/(label+'.png'));assert row['SYS_margin_above_fast_code_data']>=128,row;return row
 try:
  end=e.symbols['__iwram_bss_end'];e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(90);assert e.debug()[15]==4
  sample('map_walking',64);e.key(8);e.key(128);sample('inventory_enter',1);assert e.debug()[15]==7,e.debug();sample('inventory_description',512);assert e.debug()[15]==1,e.debug();e.key(1);e.key(2);e.key(2)
  # Reopen the original six-entry menu and enter the native equipment picker.
  e.key(8)
  for _ in range(3):e.key(128)
  e.key(1);assert e.debug()[15]==2,e.debug();sample('equipment_enter',1);assert e.debug()[15]==10,e.debug();e.key(2)
  e.key(8)
  for _ in range(4):e.key(128)
  sample('field_skill_enter',1);assert e.debug()[15]in(1,15),e.debug()
  usage=[]
  for path in(ROOT/'build').glob('*.su'):
   for line in path.read_text().splitlines():
    v=line.split('\t')
    if len(v)>2:
     try:usage.append({'function':v[0].split(':')[-1],'stack_bytes':int(v[1]),'bound':v[2]})
     except ValueError:pass
  result={'status':'pass','kind':'actual production ROM, genuine prior SAV, buttons and read-only ARM SP observation at every instruction; original audio IRQ remains active','production_rom_sha256':digest,'fast_code_data_end':end,'initial_SYS_SP':0x03007c00,'initial_IRQ_SP':0x03007fa0,'observations':rows,'largest_single_frames':sorted(usage,key=lambda r:-r['stack_bytes'])[:20],'scope':'sampled map/inventory/equipment/field skill paths; not a proof of every possible recursive call chain','physical_hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='observations'},ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
