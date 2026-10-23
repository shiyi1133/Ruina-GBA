"""Measure delivered preview response using actual LCD changes and core time.

ROM and emulated memory are never modified. Host wall time is recorded
separately; it is not substituted for the GBA timeline or a whole-game FPS.
"""
import datetime,hashlib,json,struct,time
from pathlib import Path
from drive_opening import ROOT,Emulator


def main():
    release=json.loads((ROOT/'evidence/quality_preview/delivery.json').read_text());rom=Path(release['ROM']);elf=ROOT/'build/fixtures/quality_preview/quality_preview.elf'
    digest=hashlib.sha256(rom.read_bytes()).hexdigest();assert digest==release['ROM_sha256']=='4513437665f659b3a265a57237e7f90dda5a8af5f7d72903090efa755925c5ef'
    out=ROOT/'evidence/quality_preview'/digest[:12]/'performance_20261022';assert not out.exists();out.mkdir(parents=True)
    e=Emulator(rom=rom,elf=elf);rows=[];started=time.monotonic()
    def timing():
        _,frequency,frame_cycles,frame,cycles=e.command('timing').split();return list(map(int,(frequency,frame_cycles,frame,cycles)))
    def value(name):return struct.unpack('<I',e.memory(e.symbols[name],4))[0]
    def lcd():
        _,h,black=e.command('lcdhash').split();return h,int(black)
    def action(label,key):
        e.key(0);before=lcd()[0];clock=timing();first=None;stable=0;last=None;images=[];trace=[];host_start=time.monotonic()
        for frame in range(2400):
            e.frames(1,key if frame<2 else 0);h,black=lcd();stable=stable+1 if h==last else 0;last=h
            trace.append({'frame':frame+1,'LCD_hash':h,'black_pixels':black})
            if h!=before and first is None:first=frame+1
            if h not in images:images.append(h)
            if frame>12 and stable>=6 and value('ui_ready') and not(value('input_latched')|value('input_triggered')):break
        else:raise AssertionError(('timeout',label,e.debug()))
        end=timing();assert first is not None,(label,e.debug())
        assert end[0:2]==clock[0:2] and end[2]-clock[2]==len(trace)
        final=lcd()[0];assert all(t['LCD_hash']in(before,final)for t in trace),(label,'transient LCD image')
        assert not any(t['black_pixels']==38400 for t in trace),(label,'unexpected full black')
        result={'action':label,'key':key,'press_to_first_complete_new_LCD_frames':first,'press_to_first_complete_new_LCD_ms':first*clock[1]*1000/clock[0],'observed_frames_including_post_response_settling':len(trace),'extra_settling_frames_excluded_from_latency':len(trace)-first,'host_wall_seconds_including_IPC_and_settling':time.monotonic()-host_start,'emulator_timing_before':clock,'emulator_timing_after':end,'trace':trace}
        rows.append(result);print(label,first,round(result['press_to_first_complete_new_LCD_ms'],2),'ms',flush=True)
    try:
        e.frames(180);e.key(1);assert e.debug()[15]==2 and e.debug()[17]==2
        for _ in range(3):action('view_menu_down',128);action('view_menu_up',64)
        e.key(1);assert not value('quality_fit')
        action('dialogue_to_origin_menu',1)
        for _ in range(3):action('origin_menu_down',128);action('origin_menu_up',64)
        e.key(128);e.key(1);picked=False
        for _ in range(160):
            d=e.debug();q=struct.unpack('<8I',e.memory(e.symbols['quality_debug'],32))
            assert d[0]!=0x4641554c and q[0]!=3,(d,q)
            if q[0]==2 and d[15]==4:break
            if d[15]==1:e.key(1)
            elif d[15]==2:
                if value('quality_faces')==4 and not picked:
                    for _ in range(3):action('avatar_menu_down',128);action('avatar_menu_up',64)
                    picked=True
                e.key(1)
            elif d[15]==3:
                for _ in range(3):action('name_cursor_right',16);action('name_cursor_left',32)
                action('name_insert_surname_and_switch_pool',1);action('name_insert_given',1);action('name_delete_given',2)
                action('name_tab_surnames',512);action('name_tab_given',256);action('name_restore_default',4);e.key(8)
            else:e.frames(120)
        else:raise AssertionError('opening limit')
        assert picked
        for _ in range(3):
            action('show_complete_map',4)
            action('complete_map_pan_left_8px',32);action('complete_map_pan_right_8px',16)
            action('restore_exploration_mask',4)
        e.key(8);e.key(1);e.key(1);assert e.debug()[15]==1
        action('hide_dialogue_show_illustration',4)
        for _ in range(3):action('illustration_pan_right_8px',16);action('illustration_pan_left_8px',32)
        action('restore_dialogue',2)
        summary=[]
        for label in dict.fromkeys(r['action']for r in rows):
            samples=[r for r in rows if r['action']==label];frames=[r['press_to_first_complete_new_LCD_frames']for r in samples];ms=[r['press_to_first_complete_new_LCD_ms']for r in samples]
            summary.append({'action':label,'samples':len(samples),'response_frames_min':min(frames),'response_frames_max':max(frames),'response_ms_min':min(ms),'response_ms_max':max(ms),'response_ms_mean':sum(ms)/len(ms)})
        clock=timing();result={'status':'measured','ROM':str(rom),'ROM_sha256':digest,'sample_count':len(rows),'emulator_core_frequency_Hz':clock[0],'emulator_frame_cycles':clock[1],'emulated_LCD_refresh_Hz':clock[0]/clock[1],'summary':summary,'samples':rows,'host_total_seconds_including_setup_IPC_and_settling':time.monotonic()-started,'method':'Real two-frame button pulses; complete actual LCD hash sampled every hardware frame. Latency is from pulse start to first complete new image, quantized to one frame. Six stable frames/minimum 14-frame observer windows are excluded from response time. Normal GBA core timing; no speed changes, writes or instant states.','scope':'delivered native-pixel opening preview through first-map viewer; knight origin; not whole-game FPS','hardware':'not_run','battle_or_continuous_gameplay_FPS':'not_measured','commands':e.log}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('samples','commands')},ensure_ascii=False,indent=2))
        notes=['当前开场画质预览 · 实测耗时','ROM SHA-256: '+digest,'mGBA 按 GBA 时序执行，非实机。按键开始到完整新画面出现；观察器额外等待已扣除。','这不是整场游戏 FPS。','']
        for s in summary:notes.append(f"{s['action']}: {s['response_frames_min']}–{s['response_frames_max']} 硬件帧，{s['response_ms_min']:.1f}–{s['response_ms_max']:.1f} 毫秒（{s['samples']} 次）")
        (out/'实测耗时.txt').write_text('\n'.join(notes),encoding='utf-8-sig')
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'samples':rows,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()


if __name__=='__main__':main()
