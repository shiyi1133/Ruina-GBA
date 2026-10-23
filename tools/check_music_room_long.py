"""Listen through the dense INT03 score via real music-room controls."""
import argparse,hashlib,json,math,struct,time
from pathlib import Path
from drive_opening import ROOT,Emulator
from response_meter import ResponseMeter

def main():
    p=argparse.ArgumentParser();p.add_argument('--rom');p.add_argument('--elf');p.add_argument('--loops',type=int,default=2);args=p.parse_args();assert 2<=args.loops<=1024;rom=Path(args.rom).resolve()if args.rom else ROOT/'build/废都物语_GBA_开篇开发验证版.gba';elf=Path(args.elf).resolve()if args.elf else ROOT/'build/ruina_opening_dev.elf';digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    out=ROOT/'evidence/balanced_optimization_20261023/music_room_long'/(digest[:12]+('_soak_'+str(args.loops)if args.loops!=2 else''));out.mkdir(parents=True,exist_ok=True);tracks=[t for t in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if t['kind']=='music'];index=next(i for i,t in enumerate(tracks)if t['name']=='INT03');track=tracks[index]
    e=Emulator(rom=rom,elf=elf);meter=ResponseMeter(e);started=time.monotonic()
    def read(name,n):return tuple(struct.unpack('<%dI'%n,e.memory(e.symbols[name],n*4)))
    try:
        e.frames(180);e.key(1)
        for _ in range(3):e.key(128)
        e.key(1);assert e.debug()[15]==18
        for _ in range(3):meter.action('music_list_down',128);meter.action('music_list_up',64)
        for _ in range(index):e.key(128)
        assert e.debug()[16]==index and e.debug()[19]==1,e.debug();e.key(1);e.frames(60)
        initial=read('audio_debug',8);stream=read('audio_stream_debug',4);clock=meter.timing();updates=0;observations=[]
        limit=math.ceil((track['frames']+(args.loops-1)*(track['frames']-track['loop_frame']))/16384*1.1)+30
        while read('audio_debug',8)[4]<args.loops:
            e.frames(60);audio=read('audio_debug',8);current=read('audio_stream_debug',4);midi=read('native_midi_debug',8);observations.append({'source_position':audio[3],'loops':audio[4],'underrun_samples':current[0]-stream[0],'voices':midi[2]});updates+=1
            assert current[0]==stream[0],('music-room underflow',updates,audio,current,stream)
            assert not midi[3],('cumulative voice overflow',updates,midi)
            assert updates<limit,('music-room clock stalled',audio)
            if args.loops>2 and updates%60==0:
                progress={'status':'running','ROM_sha256':digest,'target_loops':args.loops,'loops_completed':audio[4],'GBA_seconds_observed':updates*60*280896/16777216,'underrun_samples':current[0]-stream[0],'voice_overflows':midi[3]};(out/'progress.json').write_text(json.dumps(progress,indent=2));print(json.dumps(progress),flush=True)
        end=meter.timing();final=read('audio_debug',8);elapsed=(end[2]-clock[2])*clock[1]/clock[0];advance=final[3]-initial[3]+(final[4]-initial[4])*(track['frames']-track['loop_frame']);ratio=advance/(elapsed*16384);assert .999<=ratio<=1.001,ratio
        e.shot(out/'after_two_loops.png');metrics=read('music_room_video_metrics',5)if 'music_room_video_metrics'in e.symbols else None
        if metrics:assert metrics[0]==1 and metrics[3]>100,metrics
        result={'status':'pass','ROM_sha256':digest,'target_loops':args.loops,'loops_observed':final[4],'voice_overflows':0,'scope':'Real title-menu selection of INT03 in appreciation timbre, from source zero through the declared loops, actual visible seven-track list and playback timer. First60 observer frames excluded from underrun accounting only.','underruns_after_startup':0,'observed_GBA_seconds':elapsed,'source_clock_ratio':ratio,'UI_metrics':metrics,'input_response':meter.summary(),'observations':observations,'host_seconds':time.monotonic()-started,'hardware':'not_run','commands':e.log}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('commands','observations')},ensure_ascii=False,indent=2))
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()

if __name__=='__main__':main()
