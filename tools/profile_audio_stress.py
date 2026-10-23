"""Cycle profile while actual sound IRQ and dense music share a waiting UI."""
import bisect,hashlib,json,struct,subprocess
from project_env import ROOT,arm_prefix
from gba_fixture import fixture
from drive_opening import Emulator

def main():
 out=ROOT/'evidence/optimization_20261022/audio_stress_profile';out.mkdir(exist_ok=True);reports=[]
 for variant,overrides in[('normal_wave',{'light_midi':'history/quality_performance_20261022/pre_dense_timbre/light_midi.c'}),('dense_pulse',None)]:
  rom,elf,production=fixture('tests/portrait_matrix_gba.c','audio_stress_profile_'+variant,overrides);symbols=[]
  for line in subprocess.check_output([arm_prefix()+'nm','-n','-S',str(elf)],text=True).splitlines():
   p=line.split()
   if len(p)==4 and p[2].lower()=='t':symbols.append((int(p[0],16)&~1,int(p[1],16),p[3]))
  symbols.sort();starts=[p[0]for p in symbols];e=Emulator(rom=rom,elf=elf)
  try:
   for _ in range(6000):
    if e.debug()[14]==1:break
    e.frames(1)
   else:raise AssertionError(e.debug())
   e.frames(30);before=struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16));a=struct.unpack('<8I',e.memory(e.symbols['audio_debug'],32));path=out/(variant+'.txt');e.command('profile_cycles 180 0 '+str(path));after=struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16));b=struct.unpack('<8I',e.memory(e.symbols['audio_debug'],32));cycles={}
   for line in path.read_text().splitlines():
    pc,n,t=line.split();pc=int(pc,16);i=bisect.bisect_right(starts,pc)-1;name=symbols[i][2]if i>=0 and pc<symbols[i][0]+symbols[i][1]+16 else hex(pc>>24);cycles[name]=cycles.get(name,0)+int(t)
   row={'variant':variant,'underruns':after[0]-before[0],'source_clock_advance':b[3]-a[3],'source_clock_expected':180*280896/1024,'cycles':sorted(cycles.items(),key=lambda p:-p[1]),'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'production_rom_sha256':production};reports.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
  finally:e.close()
 (out/'result.json').write_text(json.dumps({'kind':'controlled actual GBA CPU cycles, dense INT03 plus four 200 percent pitch PCM effects; no UI changes during profile','reports':reports},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
