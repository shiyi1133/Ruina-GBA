"""Real save-copy success and host I/O failures must be distinguishable.

This does not change emulated state or the input ordinary SAV. /dev/full
injects a write failure; a missing parent injects an open failure.
"""
import errno,hashlib,json,struct,tempfile
from pathlib import Path
from drive_opening import ROOT,Emulator

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba'
    source=ROOT/'evidence/save_cold_load/ordinary.sav'
    digest=sha(rom);before=sha(source)
    out=ROOT/'evidence/balanced_optimization_20261023/probe_save_IO'/digest[:12]
    out.mkdir(parents=True,exist_ok=True)
    rows=[];e=Emulator(source)
    try:
        e.frames(180)
        initial=e.memory(e.symbols['game'],39704)
        with tempfile.TemporaryDirectory(prefix='ruina-save-io-')as directory:
            folder=Path(directory)
            paths=[folder/'missing_parent'/'ordinary.sav',Path('/dev/full')]
            for path,number in zip(paths,(errno.ENOENT,errno.ENOSPC)):
                reply=e.command('savecopy '+str(path))
                assert reply.startswith('SAVE_ERROR '+str(number)+' '),(path,reply)
                rows.append({'case':'open failure'if number==errno.ENOENT else'write failure','expected_errno':number,'reply':reply})
            success=folder/'中文 存档.sav'
            reply=e.command('savecopy '+str(success))
            assert reply=='SAVE 32768'and success.read_bytes()==source.read_bytes()
            rows.append({'case':'Unicode path containing a space','reply':reply,'bytes':success.stat().st_size,'input_SAV_bytes_exact':True})
            nested=folder
            for _ in range(3):nested=nested/('long-path-'+'x'*70)
            nested.mkdir(parents=True)
            success=nested/'ordinary.sav';reply=e.command('savecopy '+str(success))
            assert reply=='SAVE 32768'and success.read_bytes()==source.read_bytes()
            rows.append({'case':'long Linux extraction path','path_UTF8_bytes':len(str(success).encode()),'reply':reply,'input_SAV_bytes_exact':True})
        assert initial==e.memory(e.symbols['game'],39704),'host save copying changed the game'
        commands=e.log.copy()
    finally:e.close()
    assert sha(source)==before and sha(rom)==digest
    report={'status':'pass','production_ROM_sha256':digest,'driver_source_sha256':sha(ROOT/'tools/gba_acceptance_probe.c'),'original_SAV_sha256':before,'original_SAV_unchanged':True,'emulated_Game_unchanged':True,'cases':rows,'commands':commands,'scope':'Host-side acceptance harness file I/O only; not a gameplay or hardware test'}
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
