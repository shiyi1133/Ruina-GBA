"""Compare incremental menu output to the original full redraw reference.

This controlled eight-option cartridge verifies wrapping and scrolling;
the independent natural-opening test verifies the actual game entry path.
"""
import hashlib,json,struct
from pathlib import Path
from drive_opening import ROOT,Emulator
from gba_fixture import fixture


def main():
    b=json.loads((ROOT/'evidence/quality_preview/build.json').read_text());out=ROOT/'evidence/quality_preview'/b['ROM_sha256'][:12]/'menu_regions';out.mkdir(parents=True,exist_ok=True)
    overrides={name:'experiments/quality_preview/'+file for name,file in [('video','video.c'),('ruina_adapter','adapter.c'),('pictures','pictures.c'),('dialog','dialog.c'),('event_input','event_input.c'),('world','world.c'),('save','save.c')]}
    rom,elf,base=fixture('tests/quality_menu_fixture.c','quality_menu_regions',overrides);e=Emulator(rom=rom,elf=elf);captures=[];rows=[]
    def state():return struct.unpack('<4I',e.memory(e.symbols['quality_menu_test'],16))
    try:
        e.frames(180);e.key(0);keys=[0]+[128]*8+[64]*9
        for mode in (0,1):
            assert state()[0]==mode and e.debug()[15]==2,state()
            observed=[]
            for i,key in enumerate(keys):
                e.key(key);observed.append(e.command('lcdhash').split()[1])
                if i in(0,4,5,8,9,13,17):e.shot(out/f'mode_{mode}_step_{i:02}.png')
            captures.append(observed);rows.append({'renderer':'original full redraw'if mode else'incremental rows/list','LCD_hashes':observed});e.key(1)
        assert captures[0]==captures[1],[(i,a,c)for i,(a,c)in enumerate(zip(*captures))if a!=c]
        assert state()[1:]==(3,7,7),state()
        metrics=struct.unpack('<4I',e.memory(e.symbols['quality_menu_metrics'],16));assert metrics[0]==1 and metrics[2]>0 and metrics[3]>0,metrics
        result={'status':'pass','quality_preview_ROM_sha256':b['ROM_sha256'],'controlled_cartridge_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'base_ROM_sha256':base,'states_compared':len(keys),'pixel_hashes_match_original_full_redraw':True,'incremental_menu_metrics':metrics,'cases':rows,'scope':'controlled eight-choice scrolling/wrapping reference comparison; not an additional campaign path','commands':e.log,'hardware':'not_run'}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('commands','cases')},ensure_ascii=False,indent=2))
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'state':state(),'cases':rows,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()


if __name__=='__main__':main()
