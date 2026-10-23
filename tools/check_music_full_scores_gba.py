"""Run all original scores from their start through a complete repeat on GBA.

The core executes normal GBA timing. Host execution is unthrottled and is
reported separately. This is a controlled audio/display soak, not a campaign.
"""
import argparse,hashlib,json,math,struct,time
from drive_opening import ROOT,Emulator
from gba_fixture import fixture

FPS=16777216/280896
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--track');parser.add_argument('--quality',type=int,choices=(0,1));parser.add_argument('--video');parser.add_argument('--audio');args=parser.parse_args()
    meta=json.loads((ROOT/'build/audio_manifest.json').read_text());tracks=[t for t in meta['tracks']if t['kind']=='music'];assert len(tracks)==105
    if args.track:tracks=[t for t in tracks if t['name']==args.track];assert tracks,args.track
    cases=[(t,q)for q in((args.quality,)if args.quality is not None else(0,1))for t in tracks]
    (ROOT/'build/music_full_score_config.h').write_text('static const unsigned music_full_score_cases[][4]={'+','.join('{%d,%d,%d,%d}'%(t['id'],q,t['frames'],t['loop_frame'])for t,q in cases)+'};\n')
    base_hash=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();stem=('music_full_scores_subset_'if args.track or args.video or args.audio or args.quality is not None else'music_full_scores_')+base_hash[:12]
    rom,elf,production=fixture('tests/music_full_score_gba.c',stem,({**({'video':args.video}if args.video else{}),**({'audio':args.audio}if args.audio else{})}or None));digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    out=ROOT/'evidence/balanced_optimization_20261023/full_scores'/digest[:12];out.mkdir(parents=True,exist_ok=True);rows=[];start=time.monotonic();e=Emulator(rom=rom,elf=elf)
    def read(name,count):return tuple(struct.unpack('<%dI'%count,e.memory(e.symbols[name],count*4)))
    def save(status,current=None):
        result={'status':status,'production_rom_sha256':production,'fixture_sha256':digest,'source_bank_sha256':hashlib.sha256((ROOT/'build/audio.bin').read_bytes()).hexdigest(),'completed':len(rows),'total':len(cases),'track_filter':args.track,'quality_filter':args.quality,'video_source_override':args.video,'audio_source_override':args.audio,'emulated_audio_seconds_observed':sum(r['hardware_seconds_observed']for r in rows),'host_seconds':time.monotonic()-start,'current':current,'cases':rows,'scope':'All 105 original music sources in both simplified timbre modes, actual GBA execution from source position zero. Looping tracks include their initial play plus one complete repeat. One-second partial RGB UI updates run during playback. No seeking, ROM edits or emulator state loads. Eight startup observer frames per source are excluded only from underrun/clock measurement.','hardware':'not_run','campaign':'not_run'}
        (out/'progress.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result
    try:
        for index,(track,quality)in enumerate(cases,1):
            for _ in range(4000):
                if read('music_full_score_state',5)[0]==index:break
                e.frames(5)
            else:raise AssertionError(('start timeout',index,e.debug()))
            e.frames(8);initial=read('audio_debug',8);stream=read('audio_stream_debug',4);native=read('native_midi_debug',8);begin_frame=int(e.command('timing').split()[3]);sampled_frames=0
            looping=track['loop_frame']<track['frames'];total_samples=track['frames']+(track['frames']-track['loop_frame']if looping else 0);limit=math.ceil(total_samples/16384*FPS)+6000
            while True:
                audio=read('audio_debug',8);state=read('music_full_score_state',5)
                if(audio[4]>=2 if looping else bool(state[4])):break
                e.frames(180);sampled_frames+=180
                current_stream=read('audio_stream_debug',4);midi=read('native_midi_debug',8)
                assert current_stream[0]==stream[0],('underrun',index,track['name'],quality,sampled_frames,stream,current_stream)
                assert not midi[3],('voice overflow',index,track['name'],quality,midi)
                assert sampled_frames<=limit,('source clock stalled',index,track['name'],sampled_frames,limit,audio,state)
                save('running',{'index':index,'name':track['name'],'quality':quality,'source_position':audio[3],'loops_completed':audio[4],'GBA_seconds_in_current_source':sampled_frames/FPS})
            final=read('audio_debug',8);final_stream=read('audio_stream_debug',4);midi=read('native_midi_debug',8);end_frame=int(e.command('timing').split()[3]);elapsed=(end_frame-begin_frame)/FPS
            advance=final[3]-initial[3]+(final[4]-initial[4])*(track['frames']-track['loop_frame'])if looping else max(0,final[3]-initial[3]);expected=elapsed*16384 if looping else min(elapsed*16384,max(0,track['frames']-initial[3]));ratio=advance/expected if expected else 1
            row={'index':index,'name':track['name'],'quality':quality,'codec':track['codec'],'source_frames':track['frames'],'loop_frame':track['loop_frame'],'loops_observed':final[4]if looping else None,'raw_debug_loop_counter':final[4],'hardware_seconds_observed':elapsed,'source_clock_ratio':ratio,'underruns':final_stream[0]-stream[0],'voice_overflows':midi[3],'peak_voices':midi[1],'status':'pass'if final_stream[0]==stream[0]and not midi[3]and .998<=ratio<=1.002 else'fail'}
            rows.append(row);save('running');print(json.dumps(row,ensure_ascii=False),flush=True);assert row['status']=='pass',row
            e.frames(2,1);e.frames(2)
        result=save('pass');assert result['completed']==result['total'];(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/('latest_subset_attempt.json'if args.track or args.quality is not None else'latest_attempt.json')).write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print('PASS',len(rows),flush=True)
    except Exception as error:
        result=save('fail',{'error':repr(error)});(out/'failure.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));e.shot(out/'failure.png');raise
    finally:e.close()

if __name__=='__main__':main()
