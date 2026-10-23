"""Fresh extraction, real renamed release ROM and ordinary SAV cold load."""
import hashlib,json,tempfile,time,zipfile
from pathlib import Path
from drive_opening import ROOT,Emulator
from check_save import opening
from save_observation import save_payload,check_load

def verify_demo(archive,expected):
    archive=Path(archive);start=time.monotonic();destination=Path(tempfile.mkdtemp(prefix='ruina-v07-demo-check-',dir='/tmp'));out=ROOT/'evidence/balanced_optimization_20261023/distribution_smoke'/expected[:12];out.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive)as z:
        assert z.testzip()is None and len(z.namelist())==len(set(z.namelist()))
        assert all(not Path(n).is_absolute()and'..'not in Path(n).parts for n in z.namelist());z.extractall(destination)
    roms=list(destination.rglob('*.gba'));assert len(roms)==1;rom=roms[0];assert hashlib.sha256(rom.read_bytes()).hexdigest()==expected and not rom.with_suffix('.sav').exists()
    e=Emulator(rom=rom);commands=[]
    try:
        opening(e,1);e.shot(out/'actual_renamed_ROM_map.png');e.key(8);e.key(128);e.key(128);e.key(1);e.frames(60);assert e.debug()[15]==1,e.debug()
        save=rom.with_suffix('.sav');assert e.command('savecopy '+str(save))=='SAVE 32768'
        version,payload=save_payload(save.read_bytes());assert version==5 and e.memory(e.symbols['game'],len(payload))==payload;commands.append(e.log.copy())
    finally:e.close()
    e=Emulator(save=save,rom=rom)
    try:
        e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(240);assert e.debug()[15]==4,e.debug();loaded=check_load(e,payload);e.shot(out/'actual_renamed_ROM_cold_load.png');commands.append(e.log.copy())
    finally:e.close()
    report={'status':'pass','production_ROM_sha256':expected,'actual_demo_ZIP_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'ZIP_CRC':'pass','ROM_count':1,'same_name_SAV_shipped':False,'actual_renamed_ROM_used':str(rom),'new_game_to_first_map':True,'ordinary_saved_game_bytes_exact':len(payload),'new_process_cold_load':loaded,'emulator_states_or_memory_writes':False,'host_seconds':time.monotonic()-start,'commands':commands}
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));return report

def main():
    from deliver_balanced import STATE,read,current
    state=read(STATE);receipt=current();assert state['rom_sha256']==receipt['sha256']
    r=verify_demo(state['demo_zip'],receipt['sha256']);print(json.dumps({k:v for k,v in r.items()if k!='commands'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
