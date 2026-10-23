"""Actual-button latency, LCD stability and native map throughput.

Only read-only observations are used. GBA core cycles, not host execution
speed, define all response times. Ordinary save files are never modified.
"""
import argparse,datetime,hashlib,json,struct,time
from pathlib import Path
from drive_opening import ROOT,Emulator
from check_save import opening

def main():
    p=argparse.ArgumentParser();p.add_argument('--rom',required=True);p.add_argument('--elf',required=True);p.add_argument('--label',required=True);args=p.parse_args()
    rom=Path(args.rom).resolve();elf=Path(args.elf).resolve();digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    out=ROOT/'evidence/balanced_optimization_20261023'/digest[:12]/('performance_'+args.label);out.mkdir(parents=True,exist_ok=True)
    rows=[];processes=[];map_rebuilds=[];last_full=0;started=time.monotonic()
    def u32(e,name,offset=0):return struct.unpack('<I',e.memory(e.symbols[name]+offset,4))[0]
    def timing(e):return tuple(map(int,e.command('timing').split()[1:]))
    def lcd(e):
        _,h,b=e.command('lcdhash').split();return h,int(b)
    def presents(e):return u32(e,'video_metrics',16)+u32(e,'map_video_metrics',8)
    def sample(e,label,key):
        e.key(0);before=lcd(e);clock=timing(e);start=presents(e);trace=[];first=None;host=time.monotonic();stable=0
        for frame in range(1800):
            e.frames(1,key if frame<2 else 0);h,black=lcd(e);count=presents(e)
            ready=u32(e,'ui_ready');pending=u32(e,'input_latched')|u32(e,'input_triggered')
            trace.append({'frame':frame+1,'LCD_hash':h,'black_pixels':black,'presentations':count-start,'ready':ready,'pending':pending})
            if first is None and count!=start and h!=before[0]:first=frame+1
            stable=stable+1 if ready and not pending else 0
            if first is not None and stable>=6 and frame>=13:break
        else:raise AssertionError(('response timeout',label,e.debug()))
        end=timing(e);assert end[2]-clock[2]==len(trace),(clock,end,len(trace))
        r={'action':label,'key':key,'press_to_complete_new_LCD_frames':first,'press_to_complete_new_LCD_ms':first*clock[1]*1000/clock[0],'black_LCD_frames':sum(t['black_pixels']==38400 for t in trace),'observer_frames':len(trace),'GBA_timing_before':clock,'GBA_timing_after':end,'host_seconds_with_IPC':time.monotonic()-host,'trace':trace}
        rows.append(r);print(label,first,round(r['press_to_complete_new_LCD_ms'],2),'ms; black',r['black_LCD_frames'],flush=True)
    def close(e):
        processes.append(e.log.copy());e.close()
    e=Emulator(rom=rom,elf=elf)
    try:
        e.frames(180);e.key(1);assert e.debug()[15]==2
        for _ in range(3):sample(e,'title_menu_down',128);sample(e,'title_menu_up',64)
        e.key(1);picked=False;faces=False
        for step in range(180):
            d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
            full=u32(e,'world_metrics',28)
            if full>last_full:
                map_rebuilds.append({'total_full_rebuilds':full,'last_world_draw_ticks_16384Hz':u32(e,'world_metrics',20)});last_full=full
            if d[15]==4:break
            if d[15]==1:e.key(1)
            elif d[15]==2:
                if d[22]==1 and not picked:
                    for _ in range(3):sample(e,'origin_down',128);sample(e,'origin_up',64)
                    e.key(128);picked=True
                if not faces and d[22]==2:
                    for _ in range(3):sample(e,'avatar_down',128);sample(e,'avatar_up',64)
                    faces=True
                e.key(1)
            elif d[15]==3:
                for _ in range(3):sample(e,'name_cursor_right',16);sample(e,'name_cursor_left',32)
                sample(e,'name_select_surname',1);sample(e,'name_select_given',1);sample(e,'name_delete_given',2)
                sample(e,'name_show_surnames',512);sample(e,'name_show_given',256);sample(e,'name_restore_default',4);e.key(8)
            else:e.frames(120)
        else:raise AssertionError(('opening limit',e.debug()))
        e.frames(120);e.shot(out/'map.png')
        for i in range(3):
            sample(e,'map_walk_up',64);sample(e,'map_walk_down',128)
            sample(e,'map_open_menu',8);assert e.debug()[15]==2,e.debug()
            for _ in range(2):sample(e,'map_menu_down',128);sample(e,'map_menu_up',64)
            e.shot(out/'menu.png');sample(e,'map_close_menu',2);assert e.debug()[15]==4,e.debug()
            sample(e,'map_camera_up',256|64);sample(e,'map_camera_down',256|128)
        if 'balanced_native_ui_metrics'in e.symbols:
            native_metrics=list(struct.unpack('<8I',e.memory(e.symbols['balanced_native_ui_metrics'],32)))
        else:native_metrics=None
        e.shot(out/'map_after.png')
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'rows':rows,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:close(e)
    summary=[]
    for label in dict.fromkeys(r['action']for r in rows):
        a=[r for r in rows if r['action']==label];ms=[r['press_to_complete_new_LCD_ms']for r in a]
        summary.append({'action':label,'samples':len(a),'response_ms_min':min(ms),'response_ms_max':max(ms),'response_ms_mean':sum(ms)/len(ms),'black_frames':sum(r['black_LCD_frames']for r in a)})
    result={'status':'measured','label':args.label,'ROM':str(rom),'ROM_sha256':digest,'sample_count':len(rows),'summary':summary,'opening_full_map_rebuilds':map_rebuilds,'native_ui_metrics':native_metrics,'samples':rows,'host_total_seconds_with_IPC':time.monotonic()-started,'method':'Real two-frame input pulses; actual LCD hash plus complete GPU presentation counters sampled every hardware frame. Observer settling frames are excluded from response time. Normal GBA timing; no memory writes or instant states.','hardware':'not_run','full_gameplay':'not_run','commands':processes}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('samples','commands')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
