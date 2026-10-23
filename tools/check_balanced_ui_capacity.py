"""Actual LCD font identity and safe overflow of the retained-map UI layer."""
import hashlib,json,re,struct
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture
from build_balanced_runtime import OVERRIDES

def main():
    rom,elf,base=fixture('tests/balanced_ui_capacity_gba.c','balanced_ui_capacity',OVERRIDES);digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    out=ROOT/'evidence/balanced_optimization_20261023/ui_capacity'/digest[:12];out.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'build/assets.c').read_text();pal=np.array([int(v)for v in re.search(r'game_palette\[256\]\s*=\s*\{([^}]+)\}',source).group(1).split(',')],dtype=np.int64);colors=np.stack((pal&31,pal>>5&31,pal>>10&31),-1)
    rows=[[int(v)for v in row.split(',')]for row in re.findall(r'\{([^{}]+)\}',re.search(r'glyph_rows\[\]\[12\]=\{(.*?)\};',source,re.S).group(1))]
    e=Emulator(rom=rom,elf=elf);checks=[];background=None
    try:
        for stage in range(1,5):
            for _ in range(3000):
                if e.debug()[14]==stage:break
                e.frames(10)
            else:raise AssertionError(('stage',stage,e.debug()))
            e.frames(2);p=out/f'{stage}.png';e.shot(p);actual=np.asarray(Image.open(p).convert('RGB'),dtype=np.int64)>>3;mode=struct.unpack('<H',e.memory(0x04000000,2))[0]&7
            metrics=list(struct.unpack('<8I',e.memory(e.symbols['balanced_native_ui_metrics'],32)))
            if stage==1:background=actual.copy();assert mode==0
            else:
                case=stage-2;count=260 if case else 30;expected=np.empty(actual.shape,dtype=np.int64);expected[:]=colors[11]
                for i in range(count):
                    x=i%20*12;y=i//20*12;color=colors[1 if(i+case)%2 else 2]
                    mask=np.array([[(row>>(11-xx))&1 for xx in range(12)]for row in rows[500+i]],dtype=bool)
                    expected[y:y+12,x:x+12][mask]=color
                if case==1:expected[:,:8]=background[:,:8]
                diff=int(np.any(actual!=expected,axis=-1).sum());checks.append({'stage':stage,'glyphs':count,'hardware_mode':mode,'different_pixels':diff,'safe_capacity_fallbacks':metrics[4]})
                if diff:Image.fromarray((expected*8).astype(np.uint8)).save(out/f'{stage}_expected.png')
                assert not diff,(stage,diff)
                assert(mode==0 if stage==2 else mode==3),(stage,mode)
                if stage>=3:assert metrics[4]==1,(stage,metrics)
            e.frames(2,1);e.frames(2)
        result={'status':'pass','fixture_SHA256':digest,'base_ROM_SHA256':base,'checks':checks,'scope':'Native 4bpp UI glyphs exactly retain their source masks. An oversized 260-glyph window changes safely to RGB555, preserving the visible map through transparent cells; its next redraw keeps the fallback.','memory':'read only','hardware':'not_run','commands':e.log}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2))
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'checks':checks,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()

if __name__=='__main__':main()
