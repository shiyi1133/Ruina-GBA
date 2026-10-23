"""Cycle attribution of an isolated first view from a genuine ordinary SAV."""
import bisect,hashlib,json,struct,subprocess
from project_env import ROOT,arm_prefix
from gba_fixture import fixture
from drive_opening import Emulator

def main():
    rom,elf,base=fixture('tests/map_first_draw_profile_gba.c','map_first_draw_profile');digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/balanced_optimization_20261023/first_map_profile'/base[:12];out.mkdir(parents=True,exist_ok=True)
    symbols=[]
    for line in subprocess.check_output([arm_prefix()+'nm','-n','-S',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)==4 and fields[2].lower()=='t':symbols.append((int(fields[0],16)&~1,int(fields[1],16),fields[3]))
    symbols.sort();starts=[v[0]for v in symbols];e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf)
    try:
        for _ in range(3000):
            if e.debug()[14]==1:break
            e.frames(1)
        else:raise AssertionError(e.debug())
        e.frames(60);initial=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];path=out/'cycles.txt';e.command('profile_cycles 60 1 '+str(path));assert e.debug()[14]==2,e.debug();e.frames(2);e.shot(out/'first_view.png');cycles={}
        for line in path.read_text().splitlines():
            pc,count,total=line.split();pc=int(pc,16);index=bisect.bisect_right(starts,pc)-1;name=symbols[index][2]if index>=0 and pc<symbols[index][0]+symbols[index][1]+16 else'unmapped_'+hex(pc>>24);cycles[name]=cycles.get(name,0)+int(total)
        final=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];result={'status':'profiled','production_ROM_sha256':base,'fixture_sha256':digest,'window_GBA_frames':60,'world_metrics':list(struct.unpack('<8I',e.memory(e.symbols['world_metrics'],32))),'underrun_samples':final-initial,'cycles':sorted(cycles.items(),key=lambda v:-v[1]),'method':'Actual unchanged mGBA CPU single steps, global cycles attributed to 16-byte PC bins; genuine SAV and production functions in a controlled main. Includes post-render idle remainder in the one-second window. Not physical hardware.'}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
    finally:e.close()

if __name__=='__main__':main()
