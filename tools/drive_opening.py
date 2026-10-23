"""Read-only emulator observations with real emulated button inputs.

No state loads, memory writes, CPU calls or register changes are used.
"""
import json,subprocess,struct,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROBE=ROOT/'build/gba_acceptance_probe'
from project_env import arm_prefix
PREFIX=arm_prefix()
class Emulator:
 def __init__(self,save=None,rom=None,elf=None):
  args=[str(PROBE),str(rom or ROOT/'build/废都物语_GBA_开篇开发验证版.gba')]
  if save is not None:args.append(str(save))
  self.proc=subprocess.Popen(args,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,bufsize=1)
  assert self.proc.stdout.readline().strip()=='READY';self.log=[]
  nm=subprocess.check_output([PREFIX+'nm','-n',str(elf or ROOT/'build/ruina_opening_dev.elf')],text=True)
  self.symbols={v.split()[-1]:int(v.split()[0],16) for v in nm.splitlines() if len(v.split())==3}
 def command(self,c):
  self.log.append(c);self.proc.stdin.write(c+'\n');self.proc.stdin.flush();s=self.proc.stdout.readline().strip()
  if not s:raise RuntimeError(self.proc.stderr.read())
  return s
 def frames(self,n,key=0):return self.command(f'frames {n} {key:x}')
 def key(self,key):
  # Observe completed rendering before sending the next genuine button press.
  # Large converted scenes can span several hardware frames in phase one.
  def rendered():
   if 'ui_ready'not in self.symbols:return
   for _ in range(600):
    ready=struct.unpack('<I',self.memory(self.symbols['ui_ready'],4))[0]
    pending=struct.unpack('<I',self.memory(self.symbols['input_latched'],4))[0] if 'input_latched'in self.symbols else 0
    if 'input_triggered'in self.symbols:pending|=struct.unpack('<I',self.memory(self.symbols['input_triggered'],4))[0]
    if ready and not pending:
     self.frames(12)
     if struct.unpack('<I',self.memory(self.symbols['ui_ready'],4))[0]:return
    self.frames(12)
   raise AssertionError(('render/input not ready',self.debug()))
  rendered();self.frames(12,key);self.frames(24);rendered()
 def memory(self,addr,n):return bytes.fromhex(self.command(f'read {addr:08x} {n:x}'))
 def debug(self):return struct.unpack('<24I',self.memory(self.symbols['debug_state'],96))
 def shot(self,path):assert self.command('shot '+str(path))=='SHOT 1'
 def close(self):self.proc.stdin.write('quit\n');self.proc.stdin.flush();self.proc.wait(timeout=5)
def main():
 origin=int(sys.argv[1])if len(sys.argv)>1 else 1
 # Original creation menu: sage, knight, orphan thief, temple orphan.
 option={3:0,1:1,2:2,4:3}[origin]
 out=ROOT/'evidence'/f'origin_{origin}';out.mkdir(exist_ok=True)
 e=Emulator();steps=[];e.frames(30);e.key(1);e.key(1);e.frames(150)
 last=None;result='incomplete';origin_chosen=False
 for i in range(150):
  d=e.debug();mode=d[15];signature=(mode,d[5],d[6],d[7],d[8],d[16],d[22])
  if signature!=last:
   steps.append({'step':i,'ui_mode':mode,'opcode':d[5],'common':d[6],'event':d[7],'offset':d[8],'page_offset_or_selection':d[16],'choice_number':d[22]})
   last=signature
  if mode==5 or d[0]==0x4641554c:
   e.shot(out/'halt.png');result='unsupported_original_command';break
  if mode==4:
   actual=struct.unpack('<i',e.memory(e.symbols['game']+16,4))[0]
   assert actual==origin,(actual,origin)
   e.shot(out/'cave_first_map.png');result='opening_to_cave_reached';break
  if mode==1:
   if i<4 or d[21]%3==0:e.shot(out/f'message_{d[21]:03d}_{d[16]}.png')
   e.key(1)
  elif mode==2:
   if d[22]==1 and not origin_chosen:
    e.shot(out/'origin_choices.png')
    for _ in range(option):e.key(128)
    origin_chosen=True
   e.key(1)
  elif mode==3:e.shot(out/'name_entry.png');e.key(8)
  else:e.frames(120)
 else:result='iteration_limit'
 report={'origin':origin,'result':result,'kind':'actual GBA emulator buttons, read-only observations','steps':steps,'final_debug':list(e.debug()),'commands':e.log,'chapter_complete':False,'battle_passed':False,'save_cold_load_passed':False}
 e.close();(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k not in['steps','commands']},ensure_ascii=False),flush=True)
if __name__=='__main__':main()
