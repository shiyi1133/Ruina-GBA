"""Observe stack/audio while genuine save and new-process cold-load execute."""
import hashlib,json,re,struct
from project_env import ROOT
from drive_opening import Emulator
from save_observation import save_payload,check_load
from fast_memory_bounds import fast_memory_end

def main():
    original=ROOT/'evidence/save_cold_load/ordinary.sav';old_sha=hashlib.sha256(original.read_bytes()).hexdigest();rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/balanced_optimization_20261023/save_stack'/digest[:12];out.mkdir(parents=True,exist_ok=True);rows=[]
    def observe(e,label,key):
        result=e.command('stack 120 %x'%key);modes={int(a,16):{'minimum_SP':int(b,16),'PC':int(c,16),'instructions_observed':int(d)}for a,b,c,d in re.findall(r'([0-9a-f]{2}):([0-9a-f]{8}):([0-9a-f]{8}):(\d+)',result)}
        margin=modes[31]['minimum_SP']-fast_memory_end(ROOT/'build/ruina_opening_dev.elf');assert margin>=128,(label,margin,modes)
        rows.append({'scene':label,'SYS_margin_above_fast_code_data':margin,'modes':modes});e.frames(2);e.shot(out/(label+'.png'));return modes
    e=Emulator(original)
    try:
        e.frames(60);e.key(1);e.key(128);e.key(1);e.frames(120);assert e.debug()[15]==4,e.debug()
        e.key(8);e.key(128);e.key(128)
        before=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];observe(e,'save_game',1);after=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];assert after==before,(before,after)
        assert struct.unpack('<I',e.memory(e.symbols['save_trace'],4))[0]>=1,e.debug()
        save=out/'ordinary_test.sav';e.command('savecopy '+str(save));version,payload=save_payload(save.read_bytes());assert version==5 and e.memory(e.symbols['game'],len(payload))==payload
        save_commands=e.log.copy()
    finally:e.close()
    e=Emulator(save)
    try:
        e.frames(60);e.key(1);e.key(128);observe(e,'cold_load',1);e.frames(180);assert e.debug()[15]==4,e.debug();loaded=check_load(e,payload);load_commands=e.log.copy()
    finally:e.close()
    assert hashlib.sha256(original.read_bytes()).hexdigest()==old_sha
    result={'status':'pass','production_ROM_sha256':digest,'observations':rows,'save_music_underrun_samples':after-before,'save_version':version,'exact_cold_load':loaded,'original_SAV_unchanged':True,'scope':'Real production ROM, actual menu buttons, ordinary SRAM save and fresh-process cold load. Read CPU SP at every emulated instruction; no RAM sentinels, ROM patches or save states. Sampled call paths, not all recursion proven.','physical_hardware':'not_run','commands':[save_commands,load_commands]}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
