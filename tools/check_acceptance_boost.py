"""Real new games, learned-bit observations, actual spell use, SRAM and restart."""
import hashlib,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from check_save import opening
from save_observation import save_payload,check_load


def main():
    build=json.loads((ROOT/'evidence/acceptance_boost_20261023/build.json').read_text());rom=Path(build['ROM']);elf=Path(build['ELF']);digest=hashlib.sha256(rom.read_bytes()).hexdigest();assert digest==build['ROM_sha256']
    out=ROOT/'evidence/acceptance_boost_20261023'/digest[:12];out.mkdir(parents=True,exist_ok=True)
    skills=[s['id'] for s in build['skills']];magics=[s['id'] for s in build['skills'] if '$C' in s['name']];processes=[];checks=[]
    def new(save=None):return Emulator(save=save,rom=rom,elf=elf)
    def actor(e,aid):return e.memory(e.symbols['game']+4068+aid*196,196)
    def trace(e):return struct.unpack('<4I',e.memory(e.symbols['acceptance_boost_trace'],16))
    def assert_boosted(e):
        assert trace(e)==(1,len(build['actors']),len(skills),999),trace(e)
        managed=[]
        for aid in build['actors']:
            data=actor(e,aid);assert struct.unpack_from('<2i',data,64)==(999,999),(aid,data[64:72])
            assert struct.unpack_from('<6h',data,76)==(999,)*6,aid
            assert all(data[100+s//8]&(1<<(s%8)) for s in magics),aid
            missing=[s for s in skills if not data[100+s//8]&(1<<(s%8))]
            # Original parallel events adjust fragment ownership, companion
            # crafting/summoning and one exploration trait. These are not
            # magic spells; do not disable their original event conditions.
            assert set(missing)<={11,12,40,52,399},(aid,missing)
            if missing:managed.append({'actor':aid,'original_event_managed_skills':missing})
        return managed
    def until(phase):
        for _ in range(300):
            d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
            now=struct.unpack('<i',e.memory(e.symbols['game']+172,4))[0]
            if d[15]==4 and now==phase:return
            if d[15] in (1,2,6,7):e.key(1)
            else:e.frames(60)
        raise AssertionError(('phase not reached',phase,e.debug()))
    def select_point(eid):
        for _ in range(120):
            assert e.debug()[15]==4,e.debug()
            if e.debug()[11]==eid:e.key(1);return
            e.key(256)
        raise AssertionError(('point unavailable',eid))
    for origin in (1,2,3,4):
        e=new()
        try:
            opening(e,origin);managed=assert_boosted(e)
            data=actor(e,origin);assert data[98]==1,(origin,data[98])
            assert struct.unpack_from('<H',data,88)[0]==453
            assert e.memory(e.symbols['game']+3133+453,1)==b'\x03'
            e.key(2);e.key(1);e.shot(out/f'origin_{origin}_status.png');e.key(2)
            # The one-shot grant must not repeat when opening/closing menus.
            for _ in range(3):e.key(2);e.key(2)
            assert trace(e)[0]==1
            checks.append({'check':'fresh original origin reaches map with HP/MP and four bonuses 999, all 65 magic spells and the initial grant of 194 learnable abilities','origin':origin,'level':data[98],'grant_trace':list(trace(e)),'original_conditional_auxiliary_skills':managed,'pass':True})
            if origin!=1:continue
            select_point(1);until(2);select_point(7)
            for _ in range(350):
                d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
                if d[5]==10710 and d[15]==2 and d[19]==1:break
                if d[15] in (1,2):e.key(1)
                else:e.frames(60)
            else:raise AssertionError('first battle not reached')
            values=struct.unpack('<10i',e.memory(e.symbols['units'],40));assert values[0]==1 and values[2:]==(999,)*8,values
            e.shot(out/'battle_999.png');e.key(1);e.key(128);e.key(1)
            assert e.debug()[15]==6 and e.debug()[19]==5,e.debug()
            count=e.debug()[17];assert count>100,count;e.shot(out/'all_skills_first.png')
            e.key(64);assert e.debug()[16]==count-1;e.shot(out/'all_skills_last.png');e.key(128);assert e.debug()[16]==0
            # Read the actual list text color for every magic spell. A gray
            # label means the original weapon/state/MP rules reject it.
            checked=[];palette=struct.unpack('<16H',e.memory(e.symbols['game_palette'],32));white=palette[1]
            rgb=np.array((white&31,white>>5&31,white>>10&31))
            for position in range(count):
                sid=e.debug()[14]
                if sid in magics:
                    image=out/f'magic_{sid:03d}_usable.png';e.shot(image)
                    pixels=np.asarray(Image.open(image).convert('RGB'))>>3;y=31+min(position,5)*17
                    assert np.any(np.all(pixels[y:y+12,10:195]==rgb,axis=2)),('magic is gray despite full MP and magic blade',sid)
                    checked.append(sid)
                e.key(128)
            assert set(checked)==set(magics),(checked,magics)
            checks.append({'check':'all 65 learned magic spells actually appear enabled, verified by real battle LCD text pixels; original equipment rules unchanged','spell_ids':checked,'starting_magic_weapon':453,'pass':True})
            for _ in range(count):
                if e.debug()[14]==201:break
                e.key(128)
            else:raise AssertionError('learned arrow spell absent from battle list')
            e.shot(out/'cast_arrow_spell.png');e.key(1)
            assert e.debug()[15]==2 and e.debug()[19]==3,e.debug()
            e.key(1);saw_spell=False
            for _ in range(350):
                d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
                if d[15]==1:
                    message=e.memory(e.symbols['dialog'],8192).split(b'\0',1)[0].decode('gbk')
                    if '矢之咒' in message:saw_spell=True;e.shot(out/'spell_executed.png')
                phase=struct.unpack('<i',e.memory(e.symbols['game']+172,4))[0]
                if d[15]==4 and phase==3:break
                if d[15] in (1,2,6,7):e.key(1)
                else:e.frames(60)
            else:raise AssertionError('spell did not complete first original victory')
            hp,mp,xp=struct.unpack_from('<3i',actor(e,1),64)
            assert saw_spell and 0<hp<=999 and mp==997 and xp==1,(saw_spell,hp,mp,xp)
            assert trace(e)[0]==1;e.shot(out/'first_victory.png')
            e.key(2);e.key(2);assert struct.unpack_from('<i',actor(e,1),68)[0]==997,'menu silently healed mana'
            checks.append({'check':'actual first battle imports all six stats 999; skill list wraps; arrow spell executes and wins; MP falls 999->997 and is not silently restored','skill_choices':count,'actual_battle_unit':values,'after':{'HP':hp,'MP':mp,'XP':xp},'pass':True})
            # Existing B-menu help remains available in the variant.
            e.key(2)
            for _ in range(5):e.key(128)
            e.key(1);assert e.debug()[15]==19;e.shot(out/'controls_help.png');e.key(2);e.key(2)
            e.key(2);e.key(128);e.key(128);e.key(1);assert e.debug()[15]==1,e.debug()
            save=out/'acceptance_test.sav';assert e.command('savecopy '+str(save))=='SAVE 32768'
            version,payload=save_payload(save.read_bytes());assert version==5 and len(payload)==39704 and e.memory(e.symbols['game'],len(payload))==payload
            checks.append({'check':'original B help and actual menu save remain usable with unchanged 39704-byte v5 SRAM','pass':True})
        except Exception as error:
            e.shot(out/f'failure_{origin}.png');(out/f'failure_{origin}.json').write_text(json.dumps({'status':'fail','error':repr(error),'debug':e.debug(),'commands':e.log},ensure_ascii=False,indent=2));raise
        finally:processes.append(e.log.copy());e.close()
    e=new(save)
    try:
        e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(240);assert e.debug()[15]==4,e.debug()
        loaded=check_load(e,payload);assert trace(e)==(0,0,0,0),trace(e)
        assert struct.unpack_from('<i',actor(e,1),68)[0]==997,'load incorrectly refilled mana'
        for s in magics:assert actor(e,1)[100+s//8]&(1<<(s%8))
        e.key(2);e.key(1);e.shot(out/'cold_load_status.png')
        checks.append({'check':'fresh-process ordinary SAV retains enhanced stats, learned skills and spent MP; no repeated cheat grant after load','pass':True,'load':loaded})
    finally:processes.append(e.log.copy());e.close()
    # A pre-existing ordinary save stays ordinary; only a new game grants boosts.
    original=ROOT/'evidence/save_cold_load/ordinary.sav';before=hashlib.sha256(original.read_bytes()).hexdigest();old_payload=save_payload(original.read_bytes())[1];e=new(original)
    try:
        e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(240);assert e.debug()[15]==4
        check_load(e,old_payload);assert trace(e)==(0,0,0,0)
        checks.append({'check':'old ordinary save loads exactly without converting it into an enhanced save','pass':True})
    finally:processes.append(e.log.copy());e.close()
    assert hashlib.sha256(original.read_bytes()).hexdigest()==before
    assert hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest()==build['baseline_ROM_sha256']
    report={'status':'pass','ROM_sha256':digest,'baseline_ROM_sha256':build['baseline_ROM_sha256'],'stats':build['stats'],'initially_granted_skills':build['skill_count'],'fully_learned_magic_skills':build['magic_count'],'checks':checks,'commands':processes,'memory':'read only, real emulator buttons only','instant_states':False,'formal_ROM_and_saves':'unchanged','physical_hardware':'not_run','full_campaign':'not_run'}
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(out.parent/'validation.json').write_text(json.dumps({'status':'pass','ROM_sha256':digest,'report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='commands'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
