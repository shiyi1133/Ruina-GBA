"""Actual new-game combat response, complete LCD stability and victory."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator
from check_save import opening
from check_first_battle import settle,phase
from response_meter import ResponseMeter

def main():
    rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/balanced_optimization_20261023'/digest[:12]/'battle_response';out.mkdir(parents=True,exist_ok=True)
    e=Emulator();meter=ResponseMeter(e);skill_measured=False
    try:
        opening(e,3);e.key(1);settle(e,wanted_phase=2)
        for _ in range(100):
            if e.debug()[11]==7:break
            e.key(256)
        else:raise AssertionError('first encounter unavailable')
        e.key(1)
        for _ in range(100):
            d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
            if d[15]==2 and d[19]==1:break
            if d[15]in(1,2,6):e.key(1)
            else:e.frames(30)
        else:raise AssertionError(('battle menu not reached',e.debug()))
        e.key(0);assert struct.unpack('<H',e.memory(0x04000000,2))[0]&7==3
        for _ in range(3):meter.action('battle_mode_menu_down',128);meter.action('battle_mode_menu_up',64)
        e.shot(out/'mode_menu.png');e.key(1);assert e.debug()[15]==2 and e.debug()[19]==2,e.debug()
        for _ in range(3):meter.action('battle_actor_menu_down',128);meter.action('battle_actor_menu_up',64)
        e.shot(out/'actor_menu.png');e.key(128);e.key(1)
        if e.debug()[15]==6:
            before=e.debug()[14];e.key(128)
            if e.debug()[14]!=before:
                for _ in range(3):meter.action('battle_skill_menu_up',64);meter.action('battle_skill_menu_down',128)
                skill_measured=True
            e.shot(out/'skill_menu.png')
            for _ in range(6):
                meter.action('battle_skill_choose_target',1);assert e.debug()[15]==2 and e.debug()[19]==3,e.debug()
                meter.action('battle_skill_target_B_to_skill',2);assert e.debug()[15]==6,e.debug()
            meter.action('battle_skill_B_to_command',2)
            assert e.debug()[15]==2 and e.debug()[19]==2 and e.debug()[16]==1,e.debug()
            e.key(64) # Parent retains the skill command; select Attack for victory.
        for _ in range(200):
            d=e.debug();assert d[0]!=0x4641554c and d[15]!=5,d
            if d[15]==4 and phase(e)==3:break
            if d[15]in(1,2,6,7):e.key(1)
            else:e.frames(30)
        else:raise AssertionError(('first victory not reached',e.debug()))
        e.shot(out/'victory.png');actor=e.memory(e.symbols['game']+4068+3*196,196);hp,mp,xp=struct.unpack_from('<3i',actor,64);gold=struct.unpack('<i',e.memory(e.symbols['game']+29744,4))[0];assert xp==1 and gold==1 and mp==10,(hp,mp,xp,gold)
        assert not any(r['black_LCD_frames']or r['intermediate_LCD_frames']for r in meter.samples)
        result={'status':'measured','production_rom_sha256':digest,'scope':'Sage origin, actual opening, original first encounter, unchanged options and first victory. Real two-frame pulses; actual completed LCD hashes every hardware frame.','summary':meter.summary(),'skill_menu_had_multiple_choices':skill_measured,'victory':{'hp':hp,'mp':mp,'XP':xp,'gold':gold},'samples':meter.samples,'commands':e.log,'hardware':'not_run','full_campaign':'not_run'}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('samples','commands')},ensure_ascii=False,indent=2));assert hashlib.sha256(rom.read_bytes()).hexdigest()==digest
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'samples':meter.samples,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()

if __name__=='__main__':main()
