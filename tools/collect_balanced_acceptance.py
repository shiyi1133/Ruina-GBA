"""Collect only exact-production-hash evidence for the playable v0.7 build.

This does not run a test or turn historical reports into current passes.
Missing, incomplete and rejected reports remain visible and fail collection.
"""
import hashlib,json
from pathlib import Path
from project_env import ROOT

BASE=ROOT/'evidence/balanced_optimization_20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())

def collect():
    receipt=read(ROOT/'build/build_receipt.json');digest=sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba')
    assert receipt['sha256']==digest and all(sha(ROOT/p)==h for p,h in receipt['compiler_inputs_sha256'].items())
    rows=[]
    def accept(label,p,key,status='pass'):
        d=read(p);assert d[key]==digest,(label,'different production ROM',d.get(key))
        assert d['status']==status,(label,d['status'])
        rows.append({'name':label,'report':str(p.relative_to(ROOT)),'report_sha256':sha(p),'status':d['status']});return d
    def find(label,group,key):
        candidates=[]
        for p in(BASE/group).glob('*/result.json'):
            d=read(p)
            if d.get('video_source_override')or d.get('audio_source_override')or d.get('source_overrides'):continue
            if group=='rgb_pixels'and d.get('extra_native'):continue
            if group=='full_scores'and(d.get('total')!=210 or d.get('track_filter')is not None or d.get('quality_filter')is not None):continue
            if d.get(key)==digest and d.get('status')=='pass':candidates.append(p)
        assert len(candidates)==1,(label,'expected one passing current report',candidates)
        return accept(label,candidates[0],key)
    credits=accept('in-game attribution and unchanged title artwork',BASE/digest[:12]/'attribution/result.json','ROM_sha256')
    assert credits['attribution']=='胖胖&咩咩 移植'and credits['all_credit_glyphs_present']and credits['new_game_after_credits_reaches_map']
    regression=accept('common regression',ROOT/'evidence/optimization_20261022/final_validation'/digest[:12]/'result.json','rom_sha256')
    assert regression['completed']==regression['total']==36 and regression['compiler_inputs_unchanged']and regression['production_ROM_unchanged']
    identity=accept('original data and rules source identity',BASE/'content_identity.json','production_ROM_sha256')
    assert len(identity['unchanged_payloads'])==9 and all(sha(ROOT/r['path'])==r['SHA256']and r['same_as_v062']for r in identity['unchanged_payloads'])
    shop=accept('shop exact pixels, prices, stock and full Game state',BASE/'shop_comparison'/digest[:12]/'result.json','production_ROM_sha256')
    assert shop['shop_source_sha256']==receipt['compiler_inputs_sha256']['runtime/rm2k/shop.c']and shop['item_mask_header_sha256']==receipt['compiler_inputs_sha256']['runtime/rm2k/item_mask.h']
    inventory_files=[]
    for p in(BASE/'inventory_matrix').glob('*/result.json'):
        d=read(p)
        if d.get('production_ROM_sha256')==digest and d.get('inventory_source_sha256')==receipt['compiler_inputs_sha256']['runtime/rm2k/inventory.c']:inventory_files.append(p)
    assert len(inventory_files)==1,inventory_files
    inventory=accept('inventory original filters, return IDs and pixels',inventory_files[0],'production_ROM_sha256');assert len(inventory['cases'])==4 and sum(r['LCD_states_exact']for r in inventory['cases'])==68
    order_path=BASE/'shop_order'/(shop['shop_source_sha256'][:12]+'.json');order=read(order_path);assert order['status']=='pass'and order['source_sha256']==shop['shop_source_sha256']and order['item_mask_header_sha256']==shop['item_mask_header_sha256']and order['subsets']==1024
    rows.append({'name':'original item ID order and buying duplicates','report':str(order_path.relative_to(ROOT)),'report_sha256':sha(order_path),'status':'pass'})
    rgb=find('independent RGB555 pixels','rgb_pixels','production_baseline_SHA256');assert len(rgb['checks'])==41 and not any(c['different_pixels']for c in rgb['checks'])
    assert rgb['renderer_source_sha256']==receipt['compiler_inputs_sha256']
    menu=find('partial menu pixels','menu_regions','base_ROM_sha256');assert menu['total_states_compared']==54
    find('native text capacity and RGB fallback','ui_capacity','base_ROM_SHA256')
    maps=[]
    for p in(BASE/'map_windows').glob('*/result.json'):
        d=read(p)
        if d.get('production_ROM_sha256')==digest and not d.get('source_overrides')and d.get('music_timbre')==0:maps.append(p)
    assert len(maps)==1,('missing current native-map window matrix',maps)
    matrix=accept('all native maps: window, portrait, save and bitmap return',maps[0],'production_ROM_sha256')
    assert matrix['native_maps_tested']==61 and matrix['LCD_states_compared']==610 and not matrix['different_pixels']
    codec_sha=receipt['compiler_inputs_sha256']['runtime/rm2k/storage_codec.c']
    codec=read(BASE/'storage'/('host_'+codec_sha[:12]+'.json'));assert codec['status']=='pass'and codec['source_sha256']==codec_sha and codec['cases']==48
    rows.append({'name':'exact state codec with audio callbacks','report':str((BASE/'storage'/('host_'+codec_sha[:12]+'.json')).relative_to(ROOT)),'report_sha256':sha(BASE/'storage'/('host_'+codec_sha[:12]+'.json')),'status':'pass'})
    rooms=accept('original recipe/title effects and list pixels',BASE/'list_optimization'/digest[:12]/'result.json','candidate_ROM_sha256');assert rooms['original_event_effects_match']and rooms['music_list_hashes_match']
    for origin in range(1,5):
        accept('natural opening origin '+str(origin),BASE/digest[:12]/('opening_'+str(origin))/'result.json','ROM_sha256')
    room=accept('actual music room two loops',BASE/'music_room_long'/digest[:12]/'result.json','ROM_sha256');assert not room['underruns_after_startup']
    soak=accept('actual music room128-loop longevity',BASE/'music_room_long'/(digest[:12]+'_soak_128')/'result.json','ROM_sha256');assert soak['loops_observed']>=128 and not soak['underruns_after_startup']and not soak['voice_overflows']and soak['observed_GBA_seconds']>7200
    stack=accept('real save and cold-load stack/audio',BASE/'save_stack'/digest[:12]/'result.json','production_ROM_sha256');assert stack['original_SAV_unchanged']and not stack['save_music_underrun_samples']
    battle=accept('actual first battle and response',BASE/digest[:12]/'battle_response/result.json','production_rom_sha256','measured')
    assert not any(r['black_frames']or r['intermediate_LCD_frames']for r in battle['summary'])and battle['victory']['XP']==1 and battle['victory']['gold']==1
    battle_menu=accept('battle full redraw pixels, nested B and actual input',BASE/digest[:12]/'battle_menu_comparison.json','production_ROM_sha256');assert battle_menu['LCD_states_exact']==48 and not battle_menu['music_underruns']and battle_menu['held_repeat']['complete_cursor_changes']>=5
    performance=accept('actual map/menu response',BASE/digest[:12]/'performance_final_balance/result.json','ROM_sha256','measured')
    assert not any(r['black_frames']for r in performance['summary'])
    music=find('105 whole sources in both timbres','full_scores','production_rom_sha256')
    assert music['completed']==music['total']==210
    assert all(music.get(k)is None for k in('track_filter','quality_filter','video_source_override','audio_source_override'))
    assert all(r['status']=='pass'and not r['underruns']and not r['voice_overflows']for r in music['cases'])
    map_audio={'native_maps':matrix['native_maps_tested'],'LCD_states':matrix['LCD_states_compared'],'continuing_score_underruns':sum(r['continuing_music_underruns']for r in matrix['records']),'maximum_new_BGM_startup_silent_samples':max(s['new_BGM_startup_silent_samples']for r in matrix['records']for s in r['stages']),'note':'New score startup is separately counted and bounded to one 16-sample IRQ (about 1 ms); first-map initialization/priming is excluded. Gaps later in a score are required to be zero.'}
    result={'status':'pass','ROM_sha256':digest,'ROM_bytes':receipt['bytes'],'version':receipt['version'],'reports':rows,'common_regression_tests':regression['total'],'whole_music_cases':music['total'],'emulated_audio_seconds_observed':music['emulated_audio_seconds_observed'],'music_room_longevity':{k:soak[k]for k in('loops_observed','observed_GBA_seconds','source_clock_ratio','underruns_after_startup','voice_overflows')},'response':performance['summary'],'battle_response':battle['summary'],'battle_menu_response':battle_menu['current_response'],'native_map_matrix':map_audio,'scope':'Continuing playable build with original game data and ordinary saves. Production-ROM button checks and separate controlled pixel/audio tests are distinguished in the linked reports.','unverified':['full natural campaign and all endings','physical GBA hardware','universal PC visual and performance parity'],'source_archive_verification':'separate archive receipt required'}
    (BASE/'final_acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));return result

if __name__=='__main__':
    result=collect();print(json.dumps({k:v for k,v in result.items()if k not in('response','battle_response')},ensure_ascii=False,indent=2))
