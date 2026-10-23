"""Compare partial menu rows to full redraw in RGB, map-layer and battle UIs."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator
from gba_fixture import fixture
from build_balanced_runtime import OVERRIDES

def main():
    rom,elf,base=fixture('tests/balanced_menu_regions_gba.c','balanced_menu_regions',OVERRIDES);digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    out=ROOT/'evidence/balanced_optimization_20261023/menu_regions'/digest[:12];out.mkdir(parents=True,exist_ok=True)
    e=Emulator(rom=rom,elf=elf);rows=[]
    def state():return struct.unpack('<5I',e.memory(e.symbols['balanced_menu_test'],20))
    try:
        e.frames(180);e.key(0);keys=[0]+[128]*8+[64]*9
        for context in range(3):
            variants=[]
            for mode in range(2):
                assert state()[:3]==(context,mode,1),(context,mode,state());assert e.debug()[15]==2,e.debug();hashes=[]
                for i,key in enumerate(keys):
                    e.key(key);hashes.append(e.command('lcdhash').split()[1])
                    if i in(0,4,5,8,9,13,17):e.shot(out/f'context_{context}_renderer_{mode}_step_{i:02}.png')
                variants.append(hashes);e.key(1)
            assert variants[0]==variants[1],(context,[(i,a,b)for i,(a,b)in enumerate(zip(*variants))if a!=b])
            rows.append({'context':['title RGB555','native map BG1','battle RGB555'][context],'states_compared':len(keys),'partial_and_full_LCD_hashes':variants[0],'all_pixels_match':True})
        assert state()[2:]==(3,7,7),state()
        metrics=list(struct.unpack('<8I',e.memory(e.symbols['balanced_native_ui_metrics'],32)));assert not metrics[4],metrics
        result={'status':'pass','controlled_cartridge_sha256':digest,'base_ROM_sha256':base,'cases':rows,'total_states_compared':len(keys)*3,'native_ui_metrics':metrics,'scope':'Actual LCD comparison of full-scene reference redraw against partial row/list updates, including wraparound and scroll. Separate natural game tests cover campaign entry.','commands':e.log,'hardware':'not_run'}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2))
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'state':state(),'completed_cases':rows,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()

if __name__=='__main__':main()
