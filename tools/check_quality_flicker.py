"""Check every actual LCD frame around UI and camera key presses.

Use --old to reproduce the released 360c preview's black flashes. Memory is
read only; no state injection, emulator timing changes or register patches.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from drive_opening import ROOT,Emulator


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--old',action='store_true');args=parser.parse_args()
    if args.old:
        source=ROOT/'history/quality_flicker_fix_20261022/360c2d707509';rom=source/'quality_preview.gba';elf=source/'quality_preview.elf'
    else:
        b=json.loads((ROOT/'evidence/quality_preview/build.json').read_text());rom=Path(b['ROM']);elf=Path(b['ELF'])
    digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/quality_preview'/digest[:12]/'keypress_LCD';out.mkdir(parents=True,exist_ok=True)
    e=Emulator(rom=rom,elf=elf);cases=[]
    def value(name):return struct.unpack('<I',e.memory(e.symbols[name],4))[0]
    def lcd():
        _,h,black=e.command('lcdhash').split();return h,int(black)
    def action(name,key):
        e.key(0);before=lcd()[0];e.shot(out/(name+'_before.png'));trace=[];stable=0;last=None
        menu_before=list(struct.unpack('<4I',e.memory(e.symbols['quality_menu_metrics'],16)))if 'quality_menu_metrics'in e.symbols else None
        name_before=list(struct.unpack('<4I',e.memory(e.symbols['quality_name_metrics'],16)))if 'quality_name_metrics'in e.symbols else None
        for frame in range(2400):
            e.frames(1,key if frame<2 else 0);h,black=lcd();stable=stable+1 if h==last else 0;last=h
            trace.append({'frame':frame,'LCD_hash':h,'black_pixels':black})
            assert not struct.unpack('<H',e.memory(0x04000000,2))[0]&128
            if frame>12 and stable>=6 and value('ui_ready') and not(value('input_latched')|value('input_triggered')):break
        else:raise AssertionError(('key completion',name,e.debug()))
        after=lcd()[0];e.shot(out/(name+'_after.png'));transients=[r for r in trace if r['LCD_hash']not in(before,after)];black=[r for r in trace if r['black_pixels']==240*160]
        metrics=list(struct.unpack('<8I',e.memory(e.symbols['quality_commit_debug'],32)))if not args.old else None
        damage=list(struct.unpack('<4I',e.memory(e.symbols['quality_damage_debug'],16)))if 'quality_damage_debug'in e.symbols else None
        menu_after=list(struct.unpack('<4I',e.memory(e.symbols['quality_menu_metrics'],16)))if menu_before is not None else None
        name_after=list(struct.unpack('<4I',e.memory(e.symbols['quality_name_metrics'],16)))if name_before is not None else None
        item={'action':name,'frames_observed':len(trace),'before':before,'after':after,'transient_frames':len(transients),'fully_black_frames':len(black),'commit_metrics':metrics,'copied_damage':damage,'menu_before':menu_before,'menu_after':menu_after,'name_before':name_before,'name_after':name_after,'trace':trace};cases.append(item)
        print(name,item['frames_observed'],'transient',len(transients),'black',len(black),flush=True)
        if not args.old:assert not transients and not black and metrics[1]==0,item
        if not args.old and name in ('view_menu_down','view_menu_up','origin_down','origin_up','origin_knight','avatar_down','avatar_up'):
            assert menu_before[0]==menu_after[0] and menu_after[1]-menu_before[1]==2 and 0<damage[0]<=240*36,item
        if not args.old and name in ('name_cursor_right','name_cursor_left'):
            assert name_before[0]==name_after[0] and name_before[1]==name_after[1] and name_after[2]-name_before[2]==2 and 0<damage[0]<=240*18,item
    try:
        e.frames(180);e.key(1) # view selection menu, title remains visible
        assert e.debug()[15]==2 and e.debug()[17]==2,('view menu not reached',e.debug())
        action('view_menu_down',128);action('view_menu_up',64);e.key(1)
        assert e.debug()[15]==1
        action('dialogue_to_origin_menu',1)
        action('origin_down',128);action('origin_up',64);action('origin_knight',128);e.key(1)
        picked=False
        for _ in range(140):
            d=e.debug();q=struct.unpack('<8I',e.memory(e.symbols['quality_debug'],32))
            if q[0]==2 and d[15]==4:break
            if d[15]==1:e.key(1)
            elif d[15]==2:
                if value('quality_faces')==4 and not picked:
                    action('avatar_down',128);action('avatar_up',64);picked=True
                e.key(1)
            elif d[15]==3:
                action('name_cursor_right',16);action('name_cursor_left',32)
                if not args.old:
                    original_length=e.debug()[20]
                    action('name_insert_surname',1);assert e.debug()[17]==1 and e.debug()[20]==2
                    action('name_next_given',16);action('name_insert_given',1);assert e.debug()[20]==4
                    action('name_delete_given',2);assert e.debug()[20]==2
                    action('name_restore_original',4);assert e.debug()[20]==original_length and not e.debug()[23]
                    action('name_tab_surnames',512);action('name_tab_given',256)
                e.key(8)
            else:e.frames(120)
        else:raise AssertionError(('first map not reached',e.debug()))
        assert picked
        action('map_show_complete',4);action('map_pan_left',32);action('map_pan_up',64);action('map_pan_right',16);action('map_pan_down',128);action('map_restore_mask',4)
        state=e.memory(e.symbols['game'],39704)
        e.key(8);e.key(1);e.key(1)
        assert e.debug()[15]==1
        action('dialogue_hide_for_art',4);action('art_pan_right',16);action('art_pan_left',32);action('art_return_to_dialogue',2)
        assert e.debug()[15]==1
        metrics=struct.unpack('<8I',e.memory(e.symbols['quality_commit_debug'],32))if not args.old else None
        if args.old:assert sum(c['fully_black_frames']for c in cases)>0,'Known failure was not reproduced'
        else:assert metrics[1]==0,metrics
        result={'status':'known_released_bug_reproduced'if args.old else'pass','ROM_sha256':digest,'cases':cases,'case_count':len(cases),'LCD_frames_observed':sum(c['frames_observed']for c in cases),'fully_black_frames':sum(c['fully_black_frames']for c in cases),'transient_or_torn_frames':sum(c['transient_frames']for c in cases),'commit_metrics':metrics,'scope':'ordinary UI, dialogue inspector, first-map viewer key presses only; explicit story black cuts are a separate check','observation':'actual completed mGBA LCD output, real buttons, read-only memory','hardware':'not_run','commands':e.log}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('cases','commands')},ensure_ascii=False,indent=2))
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'debug':e.debug(),'cases':cases,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()


if __name__=='__main__':main()
