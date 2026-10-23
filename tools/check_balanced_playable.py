"""Natural opening and ordinary old-save load of the playable hybrid target."""
import argparse,hashlib,json,struct
from pathlib import Path
from drive_opening import ROOT,Emulator


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--origin',type=int,default=1);parser.add_argument('--rom');parser.add_argument('--elf');args=parser.parse_args()
    assert args.origin in (1,2,3,4)
    rom=Path(args.rom).resolve()if args.rom else ROOT/'build/废都物语_GBA_开篇开发验证版.gba';elf=Path(args.elf).resolve()if args.elf else ROOT/'build/ruina_opening_dev.elf';b={'sha256':hashlib.sha256(rom.read_bytes()).hexdigest()}
    if not args.rom:assert b['sha256']==json.loads((ROOT/'build/build_receipt.json').read_text())['sha256']
    out=ROOT/'evidence/balanced_optimization_20261023'/b['sha256'][:12]/('opening_'+str(args.origin));out.mkdir(parents=True,exist_ok=True);e=Emulator(rom=rom,elf=elf);steps=[];captures=[]
    def shot(name):e.frames(2);e.shot(out/name);captures.append(name)
    try:
        e.frames(180);e.key(0);shot('title.png');e.key(1);assert e.debug()[15]==2 and e.debug()[17]==4,e.debug();shot('title_menu.png');e.key(1);picked=False
        for i in range(220):
            d=e.debug();steps.append(list(d));assert d[0]!=0x4641554c and d[15]!=5,d
            if d[15]==4:shot('first_map.png');break
            if d[15]==1:
                if i in(0,4,6,8,10,11,14,15,16,17,18):shot(f'dialogue_{i:03}.png')
                e.key(1)
            elif d[15]==2:
                if not picked and d[17]==4:
                    for _ in range({3:0,1:1,2:2,4:3}[args.origin]):e.key(128)
                    picked=True
                if ('balanced_faces'in e.symbols and struct.unpack('<I',e.memory(e.symbols['balanced_faces'],4))[0]==4)or('balanced_faces'not in e.symbols and 'portrait_count'in e.symbols and struct.unpack('<I',e.memory(e.symbols['portrait_count'],4))[0]==4):shot('four_faces.png')
                e.key(1)
            elif d[15]==3:shot('name.png');e.key(8)
            else:e.frames(120)
        else:raise AssertionError(('opening limit',e.debug()))
        game=struct.unpack('<4i',e.memory(e.symbols['game']+29768,16));assert game[0]==23 and struct.unpack('<i',e.memory(e.symbols['game']+16,4))[0]==args.origin,game
        display=struct.unpack('<H',e.memory(0x04000000,2))[0];assert display&7==0,display
        result={'status':'pass','ROM_sha256':b['sha256'],'origin':args.origin,'new_game_reaches_first_map':True,'native_map_hardware_mode':display&7,'game_map_x_y_selection':game,'captures':captures,'steps':steps,'commands':e.log,'hardware':'not_run','whole_game':'not_run'}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('steps','commands')},ensure_ascii=False,indent=2))
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'steps':steps,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()


if __name__=='__main__':main()
