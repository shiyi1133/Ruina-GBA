"""Real title and campaign-save comparisons of incremental list interfaces."""
import hashlib,json,struct
from pathlib import Path
from drive_opening import ROOT,Emulator
from check_source_menus import Run
from gba_fixture import fixture

def main():
    rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';elf=ROOT/'build/ruina_opening_dev.elf';digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    original,reference_elf,production=fixture('source/game.c','full_room_reference',{'source_menus':'tests/source_menus_full_reference.c','music_room':'tests/music_room_full_reference.c'})
    assert production==digest
    candidate={'sha256':digest,'base':hashlib.sha256(original.read_bytes()).hexdigest()}
    out=ROOT/'evidence/balanced_optimization_20261023/list_optimization'/digest[:12];out.mkdir(parents=True,exist_ok=True);results=[];music_hashes=[]
    keys=[0]+[128]*8+[64]*9+[128]+[8,8]
    for label,cart,symbols in [('full_reference',original,reference_elf),('incremental',rom,elf)]:
        folder=out/label;folder.mkdir(exist_ok=True);e=Emulator(rom=cart,elf=symbols);hashes=[]
        try:
            e.frames(180);e.key(1)
            for _ in range(3):e.key(128)
            e.key(1);assert e.debug()[15]==18,e.debug()
            for i,key in enumerate(keys):
                e.key(key);hashes.append(e.command('lcdhash').split()[1])
                if i in(0,4,5,8,9,17,18,19,20):e.shot(folder/f'music_{i:02}.png')
            music_hashes.append(hashes)
            # Start the same real MIDI and pause in the middle of its third
            # displayed second. Footer pixels are comparable despite changed
            # renderer latency; source sample positions are never edited.
            e.key(1)
            for _ in range(1500):
                position=struct.unpack('<I',e.memory(e.symbols['audio_debug']+12,4))[0]
                if position>=int(3.2*16384):break
                e.frames(1)
            else:raise AssertionError('music clock did not advance')
            e.frames(2,1);e.frames(40);e.key(0)
            assert struct.unpack('<i',e.memory(e.symbols['music_paused'],4))[0]
            second=struct.unpack('<I',e.memory(e.symbols['audio_debug']+12,4))[0]//16384
            assert second==3,(label,second)
            e.shot(folder/'music_paused_second3.png');e.key(8);e.shot(folder/'music_paused_other_quality.png')
            metrics=list(struct.unpack('<5I',e.memory(e.symbols['music_room_video_metrics'],20)))if 'music_room_video_metrics'in e.symbols else None
            results.append({'variant':label,'music_room_metrics':metrics,'music_commands':e.log.copy()})
        finally:e.close()
        r=Run(ROOT/'history/legacy_checkpoint_v2.sav',cart,symbols,folder/'campaign')
        try:
            commands=r.run();results[-1]['campaign_checks']=r.checks;results[-1]['campaign_commands']=commands
        finally:
            if r.e.proc.poll()is None:r.e.close()
    assert music_hashes[0]==music_hashes[1],[(i,a,b)for i,(a,b)in enumerate(zip(*music_hashes))if a!=b]
    checks=[]
    files=[('music_paused_second3.png','music_paused_second3.png'),('music_paused_other_quality.png','music_paused_other_quality.png')]
    files += [('campaign/'+n,'campaign/'+n)for n in ['01_title_choices.png','02_title_acquired.png','03_alchemy_choices.png','04_medicine_created.png','05_status_with_title.png','05_cooking_ingredients.png','06_original_dish_created.png']]
    for a,b in files:
        equal=(out/'full_reference'/a).read_bytes()==(out/'incremental'/b).read_bytes();checks.append({'screen':a,'exact_pixels':equal});assert equal,a
    assert results[0]['campaign_checks']==results[1]['campaign_checks'],'Original title/recipe/save rules changed'
    result={'status':'pass','base_ROM_sha256':candidate['base'],'candidate_ROM_sha256':candidate['sha256'],'unplayed_music_list_states':len(keys),'music_list_hashes_match':True,'screens':checks,'original_event_effects_match':True,'results':results,'scope':'Natural title inputs and two genuine ordinary campaign saves, original title acquisition/SP/skills, alchemy cancel/production, cooking ingredients/product and ordinary-save cold loads. Full reference and incremental pixels compared; no memory writes or save states.','hardware':'not_run'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='results'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
