"""Cross-map UI/portrait/save/bitmap cache ownership against full redraws.

These are separate controlled cartridges, not a claim that the corresponding
story states were reached in a natural campaign. Production ROM is untouched.
"""
import argparse,hashlib,json,struct
import numpy as np
from PIL import Image
from project_env import ROOT
from gba_fixture import fixture
from drive_opening import Emulator

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--save');parser.add_argument('--codec');parser.add_argument('--state');parser.add_argument('--world');parser.add_argument('--quality',type=int,choices=[0,1],default=0);args=parser.parse_args()
    overrides={**({'save':args.save}if args.save else{}),**({'storage_codec':args.codec}if args.codec else{}),**({'state':args.state}if args.state else{}),**({'world':args.world}if args.world else{})}
    original_maps=sorted(int(p.stem[3:])for p in(ROOT/'build/original').glob('Map*.lmu'))
    # Story and custom-list maps deliberately use the bitmap renderer. Do not
    # race through their original BGM changes without presenting any scene.
    maps=[m for m in original_maps if m>=3 and m not in(13,14,15,16,17,18,19,22)]
    music=next(t['id']for t in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if t['name']=='INT03')
    (ROOT/'build/map_window_matrix_config.h').write_text('static const int window_maps[]={'+','.join(map(str,maps))+'};\nstatic const int window_music_id='+str(music)+',window_music_quality='+str(args.quality)+';\n')
    identity={'source_overrides':{k:sha(ROOT/v)for k,v in overrides.items()},'quality':args.quality,'maps':maps,'fixture_source':sha(ROOT/'tests/map_window_matrix_gba.c'),'driver':sha(__import__('pathlib').Path(__file__))}
    digest=sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba');label_hash=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:8]+'_q'+str(args.quality);out=ROOT/'evidence/balanced_optimization_20261023/map_windows'/(digest[:12]+'_'+label_hash);out.mkdir(parents=True,exist_ok=True);records=[];reference=[];different=[]
    for label,source in(('full','tests/map_window_matrix_reference_gba.c'),('cache','tests/map_window_matrix_gba.c')):
        rom,elf,base=fixture(source,'map_windows_'+label+'_'+label_hash,overrides);assert base==digest;e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf);rows=[];audio_start=None;local_screens={}
        folder=out/label;folder.mkdir(exist_ok=True)
        try:
            for stage in range(1,len(maps)*10+1):
                for _ in range(3000):
                    value=e.debug()[14]
                    if value in(stage,0x600d):break
                    e.frames(2)
                else:raise AssertionError((label,stage,e.debug()))
                if value==0x600d:break
                e.frames(2);state=struct.unpack('<4I',e.memory(e.symbols['map_window_matrix_state'],16));audio=struct.unpack('<4I',e.memory(e.symbols['audio_stream_debug'],16))
                transition=struct.unpack('<3I',e.memory(e.symbols['map_window_matrix_audio'],12));music=struct.unpack('<2I',e.memory(e.symbols['map_window_matrix_music'],8))
                startup=0
                if audio_start is None:audio_start=audio[0]
                elif state[1]==0 and music[0]!=music[1]:
                    # A brand-new score may start between a 16-sample FIFO
                    # IRQ and its first synth block. Count and bound that one
                    # startup block; never excuse gaps later in the score.
                    startup=audio[0]-audio_start;assert 0<=startup<=16,('new BGM startup gap exceeds one IRQ',state,music,startup)
                    audio_start=audio[0]
                assert audio[0]==audio_start,(label,stage,'audio underrun',audio,state,struct.unpack('<3I',e.memory(e.symbols['map_window_matrix_audio'],12)))
                path=folder/'current.png';e.shot(path);pixels=np.asarray(Image.open(path).convert('RGB')).copy();row={'stage':stage,'map':state[0],'phase':state[1],'save_ok':state[2],'completed_maps':state[3],'LCD_sha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'display_control':struct.unpack('<H',e.memory(0x04000000,2))[0],'music_before_after':music,'new_BGM_startup_silent_samples':startup,'cumulative_audio_underrun_counter':audio[0]}
                if state[1]==0:local_screens={0:pixels}
                if state[1]==3:local_screens[3]=pixels
                expected_phase=0 if state[1]in(2,6,7,9)else 3 if state[1]==5 else None
                if expected_phase is not None:
                    count=int(np.any(local_screens[expected_phase]!=pixels,axis=-1).sum());row['different_pixels_after_restore']=count
                    if count:e.shot(folder/f'failure_restore_{stage:03}.png');assert not count,row
                if state[1]==7:assert state[2],('save failed',row)
                if state[1]==1:assert struct.unpack('<I',e.memory(e.symbols['portrait_count'],4))[0]==1,('portrait not displayed',row)
                if state[1]==8:assert struct.unpack('<I',e.memory(e.symbols['balanced_faces'],4))[0]==1,('RGB portrait not displayed',row)
                if label=='full':reference.append(pixels)
                else:
                    count=int(np.any(reference[stage-1]!=pixels,axis=-1).sum());different.append(count);row['different_pixels_from_full_redraw']=count
                    if count:e.shot(folder/f'failure_{stage:03}.png');assert not count,row
                if state[1]in(0,1,8)and(state[0]in(3,23,33,56)or stage<20):e.shot(folder/f'{stage:03}_map{state[0]:03}_phase{state[1]}.png')
                rows.append(row);e.frames(2,1);e.frames(2)
                if state[1]==9:print(label,'map',state[0],'stages',len(rows),flush=True)
            assert rows and len(rows)%10==0
            records.append({'variant':label,'fixture_sha256':sha(rom),'stages':rows,'continuing_music_underruns':0,'new_BGM_startup_silent_samples':sum(r['new_BGM_startup_silent_samples']for r in rows),'first_map_priming_counter_excluded':rows[0]['cumulative_audio_underrun_counter'],'commands':e.log})
        except Exception as error:
            e.shot(folder/'failure.png');(folder/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'rows':rows,'commands':e.log},ensure_ascii=False,indent=2));raise
        finally:e.close()
    assert len(different)==len(reference)==len(records[1]['stages'])
    result={'status':'pass','production_ROM_sha256':digest,'source_overrides':overrides,'music_timbre':args.quality,'original_maps_available':len(original_maps),'native_maps_tested':len(different)//10,'LCD_states_compared':len(different),'different_pixels':sum(different),'records':records,'scope':'Controlled original-map snapshots with real production drawing/audio/save APIs; map text and portraits, warm scrolling, real SRAM compression, RGB illustration and return. Against forced complete view reconstruction. Story/custom-list maps are excluded because this checks native map cache ownership. Does not execute or validate all story events.','physical_hardware':'not_run'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='records'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
