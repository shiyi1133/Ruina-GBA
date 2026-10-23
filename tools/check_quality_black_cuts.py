"""Observe every LCD frame after naming in the direct-color preview."""
import json,struct
from pathlib import Path
from PIL import Image
from drive_opening import ROOT,Emulator


def main():
    b=json.loads((ROOT/'evidence/quality_preview/build.json').read_text());out=ROOT/'evidence/quality_preview'/b['ROM_sha256'][:12]/'black_cuts';out.mkdir(parents=True,exist_ok=True)
    e=Emulator(rom=Path(b['ROM']),elf=Path(b['ELF']));rows=[];samples=[]
    def val(name):return struct.unpack('<I',e.memory(e.symbols[name],4))[0]
    try:
        e.frames(180);e.key(1);e.key(1);picked=False
        for _ in range(160):
            d=e.debug()
            if d[15]==3:break
            if d[15]==1:e.key(1)
            elif d[15]==2:
                if not picked and d[17]==4:e.key(128);picked=True
                e.key(1)
            else:e.frames(120)
        else:raise AssertionError('name entry not reached')
        cooldown=0;pulse=0;started=False;age=0;world=0
        for frame in range(16000):
            d=e.debug();q=struct.unpack('<8I',e.memory(e.symbols['quality_debug'],32));hidden=val('cut_active');display=struct.unpack('<H',e.memory(0x04000000,2))[0];blend,unused,amount=struct.unpack('<3H',e.memory(0x04000050,6));ready=val('ui_ready')
            assert d[0]!=0x4641554c and q[0]!=3,(d,q)
            assert not display&0x80,'hardware forced-blank would show white'
            if hidden:assert (blend>>6)&3==3 and blend&4,blend # BLDY is write-only; validate actual LCD black below.
            age=age+1 if hidden else 0
            if age==3:
                p=out/f'black_{frame:05}.png';e.shot(p);black=Image.open(p).convert('RGB').getbbox()is None;samples.append({'frame':frame,'image':p.name,'actual_LCD_is_black':black});assert black,p
            rows.append({'frame':frame,'mode':d[15],'explicit_story_cut':hidden,'display_control':display,'BLDY_open_bus_not_used':amount,'ready':ready})
            if d[15]!=3:started=True
            world=world+1 if q[0]==2 and d[15]==4 and ready else 0
            if world>=3:break
            key=0
            if pulse:key=pulse;pulse=0
            elif cooldown:cooldown-=1
            elif ready and ((d[15]==3 and not started)or d[15]in(1,2)):
                key=8 if d[15]==3 else 1;pulse=key;cooldown=24
            e.frames(1,key)
        else:raise AssertionError(('frame limit',e.debug()))
        assert started and world>=3 and samples
        result={'status':'pass','ROM_sha256':b['ROM_sha256'],'frames_observed':len(rows),'hardware_forced_blank_seen':False,'explicit_story_black_samples':samples,'opening_reaches_first_map':True,'kind':'actual emulated LCD frames, real buttons, read-only observations','whole_game':'not_run','hardware':'not_run','trace':rows,'commands':e.log}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('trace','commands')},ensure_ascii=False,indent=2))
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'trace':rows,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()


if __name__=='__main__':main()
