"""Real B-menu help pages, exact visible text, nesting and paused state."""
import ast, hashlib, json, re, struct
import numpy as np
from PIL import Image
from drive_opening import ROOT, Emulator
from check_save import opening
from check_common_names import glyphs_from_cache
from response_meter import ResponseMeter
from save_observation import persistent_view


def main():
    digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest()
    out=ROOT/'evidence/ui_v071'/digest[:12]/'controls';out.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'source/maps.c').read_text()
    fragment=source.split('static const char*const lines[][7]={',1)[1].split('\n    };',1)[0]
    lines=[ast.literal_eval(s) for s in re.findall(r'"(?:\\.|[^"\\])*"',fragment)]
    assert len(lines)==35
    glyphs=glyphs_from_cache();checks=[];commands=[];responses=[]
    fixtures=[None,ROOT/'tests/fixtures/before_dead_knight.sav']
    for which,save in enumerate(fixtures):
        previous=hashlib.sha256(save.read_bytes()).hexdigest() if save else None
        e=Emulator(save=save);meter=ResponseMeter(e)
        try:
            if save:
                e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(240)
            else:opening(e)
            assert e.debug()[15]==4,e.debug()
            baseline=persistent_view(e.memory(e.symbols['game'],39704))
            e.key(2);assert e.debug()[15]==2 and e.debug()[17]==8,e.debug()
            for _ in range(5):e.key(128)
            assert e.debug()[16]==5
            if not which:e.shot(out/'b_menu_controls.png')
            meter.action('open_controls_help',1)
            assert e.debug()[15]==19 and e.debug()[16]==0 and e.debug()[17]==5,e.debug()
            for page in range(5):
                assert e.debug()[15:18]==(19,page,5),e.debug()
                if not which:
                    image=out/f'controls_{page+1}.png';e.shot(image)
                    pixels=np.asarray(Image.open(image).convert('RGB'))>>3
                    palette=struct.unpack('<16H',e.memory(e.symbols['game_palette'],32));color=palette[1]
                    rgb=np.array((color&31,color>>5&31,color>>10&31))
                    for row,text in enumerate(lines[page*7:(page+1)*7]):
                        expected=np.zeros((12,222),dtype=bool);x=0
                        for char in text:
                            width=6 if ord(char)<128 else 12
                            assert x+width<=222,('help text clipped',page,row,text)
                            code=int.from_bytes(char.encode('gbk'),'big');assert code in glyphs,char
                            for y,bits in enumerate(glyphs[code]):
                                for j in range(12):
                                    if x+j<222 and bits&(1<<(11-j)):expected[y,x+j]=True
                            x+=width
                        observed=np.all(pixels[44+row*12:56+row*12,10:232]==rgb,axis=2)
                        assert np.array_equal(observed,expected),('LCD text mismatch',page,row,text,int(np.count_nonzero(observed!=expected)))
                old=e.command('lcdhash');before=meter.presents();e.frames(120)
                assert e.command('lcdhash')==old and meter.presents()==before,'idle help repaint'
                meter.action('help_next_page_R' if page%2==0 else 'help_next_page_right',256 if page%2==0 else 16)
            assert e.debug()[16]==0,'last page did not wrap'
            meter.action('help_previous_page_L',512);assert e.debug()[16]==4
            meter.action('help_next_page_right',16);assert e.debug()[16]==0
            meter.action('help_previous_page_left',32);assert e.debug()[16]==4
            assert struct.unpack('<i',e.memory(e.symbols['engine_clock_paused'],4))[0]==1
            meter.action('help_B_returns_to_same_menu_entry',2)
            assert e.debug()[15]==2 and e.debug()[16]==5 and e.debug()[17]==8,e.debug()
            if not which:e.shot(out/'back_to_menu.png')
            # The blue player marker legitimately blinks every 16 frames.
            # Compare map-return frames with actual subsequent live states,
            # rather than treating that independent sprite animation as tear.
            observed={}
            def capture_return(frame,h,presents):
                if presents and h not in observed:
                    image=out/f'map_return_{which}_{frame}.png';e.shot(image);observed[h]=image
            row=meter.action('menu_B_returns_to_map',2,strict_pixels=False,observe=capture_return);assert e.debug()[15]==4,e.debug()
            settled=out/f'map_return_{which}_settled.png';e.shot(settled)
            expected=np.asarray(Image.open(settled).convert('RGB'))
            oam=struct.unpack('<3H',e.memory(0x07000000+120*8,6));x=oam[1]&511;y=oam[0]&255
            if x>=256:x-=512
            if y>=160:y-=256
            mask=np.ones((160,240),dtype=bool)
            if not oam[0]&0x200:mask[max(0,y):min(160,y+16),max(0,x):min(240,x+16)]=False
            for h,image in observed.items():
                actual=np.asarray(Image.open(image).convert('RGB'))
                assert np.array_equal(actual[mask],expected[mask]),('map-return damage outside blinking selected marker',h)
            assert struct.unpack('<H',e.memory(0x04000000,2))[0]&0x0707==0x0100,'native map or UI layer not restored'
            row['expected_live_map_blink']=True;row['returned_pixels_match_outside_selected_marker']=True
            assert struct.unpack('<i',e.memory(e.symbols['engine_clock_paused'],4))[0]==0
            assert persistent_view(e.memory(e.symbols['game'],39704))==baseline
            e.key(8);e.key(2);assert e.debug()[15]==4,'START menu alias broken'
            checks.append({'check':'B menu -> 5 help pages -> B same menu -> B map, no persistent changes, clock pause restored, START alias works','fixture':'new game' if save is None else save.name,'pass':True})
            responses.extend(meter.samples)
        except Exception as error:
            e.shot(out/f'failure_{which}.png');(out/f'failure_{which}.json').write_text(json.dumps({'status':'fail','error':repr(error),'debug':e.debug(),'samples':meter.samples,'commands':e.log},ensure_ascii=False,indent=2));raise
        finally:commands.append(e.log.copy());e.close()
        if save:assert hashlib.sha256(save.read_bytes()).hexdigest()==previous
    checks.append({'check':'all 35 explanation lines are unclipped and match cached glyph pixels on the real LCD','pass':True})
    assert not any(r['black_LCD_frames'] or (r['intermediate_LCD_frames'] and not r.get('returned_pixels_match_outside_selected_marker')) for r in responses)
    result={'status':'pass','rom_sha256':digest,'checks':checks,'page_count':5,'idle_frames_checked':120*5*2,'responses':responses,'commands':commands,'memory':'read only','emulator_states':False,'hardware':'not_run','full_campaign':'not_run'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
    (ROOT/'evidence/ui_v071/controls_latest.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in('responses','commands')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
