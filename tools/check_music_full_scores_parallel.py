"""All 210 complete scores on independent normal-timing mGBA workers.

Each worker cold boots the same controlled cartridge. Genuine A presses skip
unassigned earlier sources; assigned sources always start at source position
zero and run through a complete repeat. No emulated state writes or seeking.
"""
import argparse,concurrent.futures,hashlib,json,math,struct,threading,time
from drive_opening import ROOT,Emulator
from gba_fixture import fixture
FPS=16777216/280896

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--workers',type=int,default=4,choices=range(1,9));args=parser.parse_args()
    tracks=[t for t in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if t['kind']=='music'];assert len(tracks)==105
    cases=[(t,q)for q in (0,1)for t in tracks]
    (ROOT/'build/music_full_score_config.h').write_text('static const unsigned music_full_score_cases[][4]={'+','.join('{%d,%d,%d,%d}'%(t['id'],q,t['frames'],t['loop_frame'])for t,q in cases)+'};\n')
    base=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest()
    rom,elf,production=fixture('tests/music_full_score_gba.c','music_full_scores_parallel_'+base[:12]);digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    out=ROOT/'evidence/balanced_optimization_20261023/full_scores'/(digest[:12]+'_parallel_'+str(args.workers));out.mkdir(parents=True,exist_ok=True)
    rows=[];lock=threading.Lock();started=time.monotonic();ranges=[(i*len(cases)//args.workers,(i+1)*len(cases)//args.workers)for i in range(args.workers)];failures=[]
    def report(status):
        return {'status':status,'production_rom_sha256':production,'fixture_sha256':digest,'source_bank_sha256':hashlib.sha256((ROOT/'build/audio.bin').read_bytes()).hexdigest(),'completed':len(rows),'total':210,'track_filter':None,'quality_filter':None,'video_source_override':None,'audio_source_override':None,'emulated_audio_seconds_observed':sum(r['hardware_seconds_observed']for r in rows),'host_seconds':time.monotonic()-started,'workers':args.workers,'case_ranges_zero_based_exclusive':ranges,'cases':sorted(rows,key=lambda r:r['index']),'failures':failures,'scope':'All 105 original music sources in both simplified timbres, normal GBA timing and one-second RGB UI updates. Independent cold-boot mGBA processes press A to skip their unassigned prefixes. Every assigned source is observed from position zero through initial play plus a full repeat; no seeking, memory writes or instant states. Eight startup observer frames excluded from underrun/clock checks.','hardware':'not_run','campaign':'not_run'}
    def worker(number,first,last):
        e=Emulator(rom=rom,elf=elf)
        def read(name,count):return struct.unpack('<%dI'%count,e.memory(e.symbols[name],count*4))
        def ready(index):
            for _ in range(4000):
                if read('music_full_score_state',5)[0]==index:return
                e.frames(5)
            raise AssertionError(('start timeout',number,index,e.debug()))
        try:
            for skip in range(first):
                ready(skip+1);e.frames(8);e.frames(2,1);e.frames(2)
            for local in range(first,last):
                index=local+1;track,quality=cases[local];ready(index);e.frames(8)
                initial=read('audio_debug',8);stream=read('audio_stream_debug',4);begin=int(e.command('timing').split()[3]);sampled=0
                looping=track['loop_frame']<track['frames'];total_samples=track['frames']+(track['frames']-track['loop_frame']if looping else 0);limit=math.ceil(total_samples/16384*FPS)+6000
                while True:
                    audio=read('audio_debug',8);state=read('music_full_score_state',5)
                    if(audio[4]>=2 if looping else bool(state[4])):break
                    e.frames(180);sampled+=180;current=read('audio_stream_debug',4);midi=read('native_midi_debug',8)
                    assert current[0]==stream[0],('underrun',index,track['name'],quality,sampled,stream,current)
                    assert not midi[3],('voice overflow',index,track['name'],quality,midi)
                    assert sampled<=limit,('source clock stalled',index,track['name'],sampled,limit,audio,state)
                final=read('audio_debug',8);current=read('audio_stream_debug',4);midi=read('native_midi_debug',8);end=int(e.command('timing').split()[3]);elapsed=(end-begin)/FPS
                advance=final[3]-initial[3]+(final[4]-initial[4])*(track['frames']-track['loop_frame'])if looping else max(0,final[3]-initial[3]);expected=elapsed*16384 if looping else min(elapsed*16384,max(0,track['frames']-initial[3]));ratio=advance/expected if expected else 1
                row={'index':index,'worker':number,'name':track['name'],'quality':quality,'codec':track['codec'],'source_frames':track['frames'],'loop_frame':track['loop_frame'],'loops_observed':final[4]if looping else None,'hardware_seconds_observed':elapsed,'source_clock_ratio':ratio,'underruns':current[0]-stream[0],'voice_overflows':midi[3],'peak_voices':midi[1],'status':'pass'if current[0]==stream[0]and not midi[3]and .998<=ratio<=1.002 else'fail'}
                with lock:
                    rows.append(row);(out/'progress.json').write_text(json.dumps(report('running'),ensure_ascii=False,indent=2));print(json.dumps({k:row[k]for k in('index','worker','name','quality','underruns','status')},ensure_ascii=False),flush=True)
                assert row['status']=='pass',row
                e.frames(2,1);e.frames(2)
        except Exception as error:
            with lock:
                failures.append({'worker':number,'error':repr(error)});(out/'failure.json').write_text(json.dumps(report('fail'),ensure_ascii=False,indent=2))
            raise
        finally:e.close()
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)as pool:
        futures=[pool.submit(worker,i,*bounds)for i,bounds in enumerate(ranges)]
        for future in concurrent.futures.as_completed(futures):future.result()
    assert not failures and len(rows)==210 and {r['index']for r in rows}==set(range(1,211))
    assert production==base==hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest()
    result=report('pass');(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out/'progress.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print('PASS 210',flush=True)
if __name__=='__main__':main()
