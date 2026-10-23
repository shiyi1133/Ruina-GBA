"""Save through the in-game menu, terminate, cold-load only ordinary SRAM SAV."""
import json,struct,hashlib
from drive_opening import Emulator,ROOT
from save_observation import check_load,save_payload

def opening(e,origin=1):
 e.frames(30);e.key(1);e.key(1);e.frames(150);picked=False
 for _ in range(150):
  d=e.debug()
  if d[0]==0x4641554c or d[15]==5:raise AssertionError(('halt',d))
  if d[15]==4:return
  if d[15]==1:e.key(1)
  elif d[15]==2:
   if d[22]==1 and not picked:
    for _ in range({3:0,1:1,2:2,4:3}[origin]):e.key(128)
    picked=True
   e.key(1)
  elif d[15]==3:e.key(8)
  else:e.frames(120)
 raise AssertionError('opening did not reach the cave')

def main():
 out=ROOT/'evidence/save_cold_load';out.mkdir(exist_ok=True)
 save=out/'ordinary.sav';e=Emulator();opening(e);e.frames(60);e.shot(out/'before_save.png')
 e.key(8);e.key(128);e.key(128);e.key(1);e.frames(60)
 assert e.debug()[15]==1,e.debug()
 e.shot(out/'save_message.png')
 assert e.command('savecopy '+str(save)).startswith('SAVE ')
 b=save.read_bytes();magic,version,n,source,crc=struct.unpack_from('<5I',b)
 assert magic==0x41554952 and version==5 and source==0x589a0adb
 version,payload=save_payload(b);n=len(payload);assert e.memory(e.symbols['game'],n)==payload
 e.key(1);e.frames(60)
 for _ in range(10):
  if e.debug()[15]==4:break
  e.frames(120)
 assert e.debug()[15]==4,e.debug()
 commands1=e.log.copy();e.close()
 # New process. No state files or CPU/register/memory mutation commands.
 loaded=Emulator(save);loaded.frames(30);loaded.key(1);loaded.key(128);loaded.key(1);loaded.frames(240)
 assert loaded.debug()[15]==4,loaded.debug()
 state_check=check_load(loaded,payload)
 loaded.shot(out/'after_cold_load.png');commands2=loaded.log.copy();loaded.close()
 report={'rom_sha256':hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest(),'test':'ordinary SAV cold load in a fresh emulator process','status':'pass','game_state_bytes_compared':n,'savedata_bytes':len(b),'sav_sha256':hashlib.sha256(b).hexdigest(),'save_message_paused_game_byte_match':True,'load_observations':state_check,'input':'actual emulated keys','memory_observations':'read only','emulator_states_used':False,'save_process_commands':commands1,'load_process_commands':commands2,'chapter_playthrough':'not_run'}
 (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if not k.endswith('_commands')},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
