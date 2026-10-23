"""Old full-vector renderer versus current item masks/partial inventory UI."""
import argparse,hashlib,json,re,struct
from pathlib import Path
from project_env import ROOT
from gba_fixture import fixture
from drive_opening import Emulator
from response_meter import ResponseMeter

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def field(raw,target):
    at=0
    def number():
        nonlocal at
        n=0
        while True:
            b=raw[at];at+=1;n=(n<<7)|(b&127)
            if not b&128:return n
    while at<len(raw):
        key=number()
        if not key:break
        size=number();value=raw[at:at+size];at+=size
        if key==target:return value
    return b''
def main():
    p=argparse.ArgumentParser();p.add_argument('--inventory',default='runtime/rm2k/inventory.c');args=p.parse_args();source=ROOT/args.inventory;digest=sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba')
    music=next(t for t in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if t['name']=='INT03');peak=next(t for t in json.loads((ROOT/'evidence/optimization_20261022/music/complete_score_census.json').read_text())['tracks']if t['name']=='INT03'and t['quality']==0)
    out=ROOT/'evidence/balanced_optimization_20261023/inventory_matrix'/(digest[:12]+'_'+sha(source)[:8]);out.mkdir(parents=True,exist_ok=True);cases=[]
    for rgb,mode in((0,0),(0,3),(1,0),(1,3)):
        (ROOT/'build/inventory_matrix_config.h').write_text('static const int inventory_mode=%d,inventory_rgb=%d,inventory_music_id=%d;static const unsigned inventory_music_peak=%d;\n'%(mode,rgb,music['id'],max(0,peak['peak_source_position']-32768)))
        variants=[]
        for label,path in(('full','tests/inventory_full_reference.c'),('candidate',args.inventory)):
            rom,elf,base=fixture('tests/inventory_matrix_gba.c','inventory_matrix_%d_%d_%s'%(rgb,mode,label),{'inventory':path});assert base==digest;e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf);meter=ResponseMeter(e);folder=out/('rgb%d_mode%d_%s'%(rgb,mode,label));folder.mkdir(exist_ok=True);screens=[];stack=[];selections=[]
            def capture(name):
                e.frames(2);p=folder/(name+'.png');e.shot(p);screens.append((name,p.read_bytes()));selections.append(list(e.debug()[16:19]))
            def observe(name,key):
                result=e.command('stack 120 %x'%key);m=re.findall(r'1f:([0-9a-f]{8}):([0-9a-f]{8}):(\d+)',result);assert m,result;margin=int(m[0][0],16)-e.symbols['__iwram_bss_end'];stack.append({'scene':name,'SYS_margin_above_fast_code_data':margin});assert margin>=128,(rgb,mode,label,name,margin)
            try:
                for _ in range(3000):
                    if e.debug()[14]==1:break
                    e.frames(1)
                else:raise AssertionError(e.debug())
                e.frames(60);audio=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];observe('entry',1);assert e.debug()[15]==7 and e.debug()[17]>10,e.debug();capture('00_entry')
                hardware=struct.unpack('<H',e.memory(0x04000000,2))[0]&7;assert hardware==(3 if rgb else 0),(rgb,hardware)
                keys=[128]*6+[64]*7+[128]
                for i,key in enumerate(keys,1):meter.action('list_'+('down'if key==128 else'up'),key);capture('%02d_move'%i)
                for _ in range(e.debug()[17]):
                    item=e.debug()[18];address,size=struct.unpack('<2I',e.memory(e.symbols['item_data']+item*8,8))
                    if field(e.memory(address,size),2):break
                    e.key(128)
                else:raise AssertionError('No original item description')
                observe('description',512);assert e.debug()[15]==1,e.debug();capture('description')
                for _ in range(10):
                    if e.debug()[15]==7:break
                    e.key(1)
                else:raise AssertionError(e.debug())
                capture('description_return');selected=e.debug()[18];e.key(1);assert e.debug()[14]==2 and struct.unpack('<I',e.memory(e.symbols['inventory_matrix_result'],4))[0]==selected
                final_audio=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];assert final_audio==audio,(label,rgb,mode,final_audio-audio)
                state=e.memory(e.symbols['game'],39704)
                variants.append({'variant':label,'fixture_sha256':sha(rom),'selections':selections,'returned_item':selected,'post_Game_sha256':hashlib.sha256(state).hexdigest(),'stack':stack,'input_response':meter.summary(),'continuing_music_underruns':final_audio-audio,'screens':screens,'commands':e.log})
            except Exception as error:
                e.shot(folder/'failure.png');(folder/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'stack':stack,'commands':e.log},ensure_ascii=False,indent=2));raise
            finally:e.close()
        a,b=variants;assert a['selections']==b['selections']and a['returned_item']==b['returned_item']and a['post_Game_sha256']==b['post_Game_sha256']
        assert a['screens']==b['screens'],('pixel mismatch',rgb,mode,[x[0]for x,y in zip(a['screens'],b['screens'])if x!=y])
        count=len(a['screens'])
        for v in variants:v.pop('screens')
        cases.append({'RGB':bool(rgb),'battle_item_actor_filter':mode,'LCD_states_exact':count,'variants':variants});print('PASS context',rgb,mode,count,flush=True)
    result={'status':'pass','production_ROM_sha256':digest,'inventory_source':args.inventory,'inventory_source_sha256':sha(source),'cases':cases,'scope':'Controlled original item DB and actor eligibility in native-map and RGB contexts. Original vector/full render versus mask/partial render, wrap/scroll, real description portrait, exact returned item and full Game-state hash. All item counts99 only in fixture; no natural campaign claim.','hardware':'not_run'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('PASS',digest)

if __name__=='__main__':main()
