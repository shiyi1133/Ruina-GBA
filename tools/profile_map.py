"""Observe instruction PCs while real held keys exercise the production map.
Counts are instructions, not cycle counts; audio and display counters are read
independently. This never changes emulated memory, registers or timing.
"""
import bisect,hashlib,json,struct,subprocess,sys
from project_env import ROOT,arm_prefix
from drive_opening import Emulator

def main():
 cycle_mode='--cycles'in sys.argv;digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/profiles'/(digest[:12]+('_cycles'if cycle_mode else''));out.mkdir(parents=True,exist_ok=True)
 symbols=[]
 for line in subprocess.check_output([arm_prefix()+'nm','-n','-S',str(ROOT/'build/ruina_opening_dev.elf')],text=True).splitlines():
  v=line.split()
  if len(v)==4 and v[2].lower()=='t':symbols.append((int(v[0],16)&~1,int(v[1],16),v[3]))
 symbols.sort();starts=[v[0]for v in symbols];e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav');rows=[]
 try:
  e.frames(60);e.key(1);e.key(128);e.key(1);e.frames(120);assert e.debug()[15]==4,e.debug()
  for name,key in [('idle',0),('walking_up',64),('camera_up',320)]:
   before=struct.unpack('<8I',e.memory(e.symbols['world_metrics'],32));stream_before=struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16));clock_before=struct.unpack('<I',e.memory(e.symbols['audio_debug']+12,4))[0];path=out/(name+'.txt');response=e.command(('%s 120 %%x %%s'%('profile_cycles'if cycle_mode else'profile_keys'))%(key,path));counts={};regions={};cycle_counts={}
   for line in path.read_text().splitlines():
    fields=line.split();a=int(fields[0],16);n=int(fields[1]);cycles=int(fields[2])if len(fields)>2 else 0;i=bisect.bisect_right(starts,a)-1
    label=symbols[i][2]if i>=0 and a<symbols[i][0]+symbols[i][1]+16 else 'unmapped_'+hex(a>>24)
    counts[label]=counts.get(label,0)+n;region=hex(a>>24);regions[region]=regions.get(region,0)+n;cycle_counts[label]=cycle_counts.get(label,0)+cycles
   after=struct.unpack('<8I',e.memory(e.symbols['world_metrics'],32));row={'scene':name,'profile_response':response.split()[:3],'instruction_counts':sorted(counts.items(),key=lambda p:-p[1])[:40],'regions':regions,'world_metrics_before':before,'world_metrics_after':after,'debug':e.debug(),'audio_stream_debug':struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16))}
   if 'lcf_cache_debug'in e.symbols:row['lcf_cache_debug']=struct.unpack('<8I',e.memory(e.symbols['lcf_cache_debug'],32))
   row['audio_underruns_during_profile']=row['audio_stream_debug'][0]-stream_before[0];row['bgm_clock_delta']=struct.unpack('<I',e.memory(e.symbols['audio_debug']+12,4))[0]-clock_before
   if cycle_mode:row['cycle_counts']=sorted(cycle_counts.items(),key=lambda p:-p[1])[:40];row['total_cycles']=sum(cycle_counts.values())
   rows.append(row)
  report={'rom_sha256':digest,'method':'actual held keys, '+('mGBA global timing deltas attributed to observed PC bins (instruction boundaries approximate)'if cycle_mode else'PC instruction counts (not cycles)')+', ordinary save, no emulated writes','rows':rows};(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)
 finally:e.close()

if __name__=='__main__':main()
