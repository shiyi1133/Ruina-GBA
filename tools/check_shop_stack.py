"""Dense original-item shop UI under the real event VM and dense MIDI."""
import argparse,hashlib,json,re,struct
from project_env import ROOT
from gba_fixture import fixture
from drive_opening import Emulator
from response_meter import ResponseMeter

def main():
    p=argparse.ArgumentParser();p.add_argument('--face',action='store_true');p.add_argument('--shop');p.add_argument('--gold',type=int,default=12345);args=p.parse_args();assert 0<=args.gold<=999999
    music=next(t for t in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if t['name']=='INT03')
    peak=next(t for t in json.loads((ROOT/'evidence/optimization_20261022/music/complete_score_census.json').read_text())['tracks']if t['name']=='INT03'and t['quality']==0)
    (ROOT/'build/shop_stack_config.h').write_text('static const int shop_music_id=%d,shop_face_enabled=%d,shop_initial_gold=%d;static const unsigned shop_music_peak=%d;\n'%(music['id'],args.face,args.gold,max(0,peak['peak_source_position']-32768)))
    shop_source=ROOT/(args.shop or'runtime/rm2k/shop.c');shop_sha=hashlib.sha256(shop_source.read_bytes()).hexdigest()
    fixture_source_sha=hashlib.sha256((ROOT/'tests/shop_stack_gba.c').read_bytes()).hexdigest()
    rom,elf,base=fixture('tests/shop_stack_gba.c','shop_stack_'+('face'if args.face else'plain')+('_trial'if args.shop else''),{'shop':args.shop}if args.shop else None);out=ROOT/'evidence/balanced_optimization_20261023/shop_stack'/base[:12]/(hashlib.sha256((__import__('pathlib').Path(__file__).read_bytes()+str(args).encode()+shop_sha.encode()+fixture_source_sha.encode())).hexdigest()[:8]);out.mkdir(parents=True,exist_ok=True);e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf);rows=[]
    meter=ResponseMeter(e)
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
    def integer(raw):
        n=0
        for b in raw:
            n=(n<<7)|(b&127)
            if not b&128:return n
        return n
    def observe(label,key):
        before=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];response=e.command('stack 120 %x'%key);modes={int(a,16):{'minimum_SP':int(b,16),'PC':int(c,16),'instructions':int(d)}for a,b,c,d in re.findall(r'([0-9a-f]{2}):([0-9a-f]{8}):([0-9a-f]{8}):(\d+)',response)}
        after=struct.unpack('<I',e.memory(e.symbols['audio_stream_debug'],4))[0];margin=modes[31]['minimum_SP']-e.symbols['__iwram_bss_end'];row={'scene':label,'SYS_margin_above_fast_code_data':margin,'music_underrun_samples':after-before,'modes':modes,'UI':list(e.debug())};rows.append(row);e.frames(2);e.shot(out/(label+'.png'));print(json.dumps(row),flush=True);assert margin>=128,row;assert before==after,row;return row
    try:
        for _ in range(3000):
            if e.debug()[14]==1:break
            e.frames(1)
        else:raise AssertionError(e.debug())
        e.frames(60);observe('original_event_shop_entry',1);assert e.debug()[15]==2,e.debug();e.key(0);e.key(128);observe('dense_sell_list',1);assert e.debug()[15]==8 and e.debug()[17]>100,e.debug()
        e.key(0)
        for _ in range(3):meter.action('shop_sell_down',128);meter.action('shop_sell_up',64)
        for _ in range(471):
            item=e.debug()[18];address,size=struct.unpack('<2I',e.memory(e.symbols['item_data']+item*8,8))
            if field(e.memory(address,size),2):break
            e.key(128)
        else:raise AssertionError('No item with an original description')
        observe('item_description',512);assert e.debug()[15]==1,e.debug()
        for _ in range(10):
            if e.debug()[15]==8:break
            e.key(1)
        else:raise AssertionError(('description did not return',e.debug()))
        e.key(0);observe('sell_quantity',1);assert e.debug()[15]==9,e.debug()
        layout=struct.unpack('<5I',e.memory(e.symbols['shop_state_layout'],20));price=integer(field(e.memory(address,size),5))//2;assert price>0
        gold_before=struct.unpack('<i',e.memory(e.symbols['game']+layout[1],4))[0]
        for label,key in [('quantity_plus1',16),('quantity_minus1',32),('quantity_plus10',256),('quantity_minus10',512)]:meter.action(label,key);e.shot(out/(label+'.png'))
        for _ in range(10):e.key(256)
        assert e.debug()[16]==99,e.debug();e.key(1);assert e.debug()[15]==8,e.debug()
        assert e.memory(e.symbols['game']+layout[0]+item,1)==b'\0'
        assert e.memory(e.symbols['game']+layout[2]+item*layout[4],layout[4])==b'\0'*layout[4]
        gold_after=struct.unpack('<i',e.memory(e.symbols['game']+layout[1],4))[0];assert gold_after==min(999999,gold_before+99*price)
        e.key(1);assert e.debug()[15]==8,e.debug() # sold-out row stays until list is reopened
        e.key(2);e.key(128);e.key(1);assert e.debug()[15]==8 and e.debug()[17]==470,e.debug()
        e.shot(out/'after_sell_reopened.png');e.key(2);e.key(1);assert e.debug()[15]==8,e.debug();observe('buy_quantity_limit',1);assert e.debug()[15]==8,e.debug()
        state=e.memory(e.symbols['game'],layout[3]);(out/'post_shop_state.bin').write_bytes(state)
        result={'status':'pass','production_ROM_sha256':base,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'portrait_in_description':args.face,'shop_source_override':args.shop,'shop_source_sha256':shop_sha,'test_fixture_source_sha256':fixture_source_sha,'initial_gold':args.gold,'observations':rows,'input_response':meter.summary(),'transaction':{'sold_item':item,'count':99,'unit_sale_price':price,'gold_before':gold_before,'gold_after':gold_after,'remaining_item_count':0,'usage_counter_cleared':True,'reopened_sell_list_count':470,'post_shop_Game_sha256':hashlib.sha256(state).hexdigest()},'scope':'Separate controlled cartridge: original DB, real event-VM Shop command, all original item counts at99 and high gold only in this fixture, INT03 near its dense section in game timbre. Genuine UI buttons and read-only SP observation; release data/ROM unchanged. Not natural campaign acceptance.','hardware':'not_run','commands':e.log}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print('PASS',base)
    except Exception as error:
        e.shot(out/'failure.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':repr(error),'rows':rows,'commands':e.log},ensure_ascii=False,indent=2));raise
    finally:e.close()

if __name__=='__main__':main()
