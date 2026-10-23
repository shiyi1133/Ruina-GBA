"""Capture actual unchanged v0.6.2 for comparison, with original buttons."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator


def main():
    rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=hashlib.sha256(rom.read_bytes()).hexdigest();assert digest=='1db4e8b86af4cc3b4e71abdc983f9a8e5a2c84eb5784738258912a75750e1561'
    out=ROOT/'evidence/quality_preview/baseline_v062';out.mkdir(parents=True,exist_ok=True)
    e=Emulator();captures=[]
    def shot(name):e.frames(2);e.shot(out/name);captures.append(name)
    try:
        e.frames(120);e.key(0);shot('title.png');e.key(1);e.key(1);picked=False
        for i in range(180):
            d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
            if d[15]==4:shot('first_map.png');break
            if d[15]==1:
                if i in(0,4,6,8,10,11,14,15,16,17,18):shot(f'dialogue_{i:03}.png')
                e.key(1)
            elif d[15]==2:
                if not picked and d[17]==4:e.key(128);picked=True
                if d[22]==3:shot('four_original_faces.png')
                e.key(1)
            elif d[15]==3:shot('name.png');e.key(8)
            else:e.frames(120)
        else:raise AssertionError(('opening limit',e.debug()))
        report={'status':'pass','ROM_sha256':digest,'scope':'unchanged v0.6.2, actual new-game knight opening and first map','captures':captures,'commands':e.log,'memory':'read only','instant_states':False,'hardware':'not_run'}
        (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='commands'},ensure_ascii=False,indent=2))
    finally:e.close()


if __name__=='__main__':main()
