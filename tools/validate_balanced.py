"""Current playable-ROM regression plus the new retained-map/RGB acceptance.

Use --new-only when the same-hash common regression is already running or
complete. --skip-music leaves this run partial and never collects final pass.
"""
import argparse,hashlib,json,os,subprocess,sys,time
from project_env import ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--new-only',action='store_true');p.add_argument('--skip-music',action='store_true');args=p.parse_args()
    rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';elf=ROOT/'build/ruina_opening_dev.elf';receipt=json.loads((ROOT/'build/build_receipt.json').read_text());digest=sha(rom);assert receipt['sha256']==digest
    media=os.environ.get('RUINA_ASSET_PYTHON',sys.executable);tests=[]
    if not args.new_only:tests.append(('common_regression',[media,'tools/validate_optimization.py']))
    for name,python in [('check_attribution',sys.executable),('check_battle_menu_comparison',sys.executable),('check_serviced_storage',sys.executable),('check_balanced_rgb',media),('check_balanced_menu_regions',sys.executable),('check_balanced_ui_capacity',media),('check_map_window_matrix',media),('check_incremental_rooms',media),('check_music_room_long',sys.executable),('measure_balanced_battle',sys.executable),('check_save_stack',sys.executable),('check_shop_item_order',sys.executable),('check_shop_comparison',sys.executable),('check_inventory_matrix',sys.executable)]:tests.append((name,[python,'tools/'+name+'.py']))
    for origin in range(1,5):tests.append(('natural_opening_'+str(origin),[sys.executable,'tools/check_balanced_playable.py','--origin',str(origin)]))
    tests.append(('input_response',[sys.executable,'tools/measure_balanced_response.py','--rom',str(rom),'--elf',str(elf),'--label','final_balance']))
    if not args.skip_music:
        tests.append(('whole_music',[sys.executable,'tools/check_music_full_scores_parallel.py']))
        tests.append(('actual_music_room_128_loops',[sys.executable,'tools/check_music_room_long.py','--loops','128']))
    out=ROOT/'evidence/balanced_optimization_20261023/validation'/digest[:12]/str(time.time_ns());out.mkdir(parents=True);rows=[]
    for name,command in tests:
        assert sha(rom)==digest and all(sha(ROOT/p)==h for p,h in receipt['compiler_inputs_sha256'].items()),'Production changed during validation'
        started=time.monotonic();log=out/(name+'.log');print('checking',name,flush=True)
        with log.open('w')as stream:result=subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
        rows.append({'name':name,'command':command,'status':'pass'if not result.returncode else'fail','returncode':result.returncode,'host_seconds':time.monotonic()-started,'log':str(log.relative_to(ROOT))})
        report={'status':'running'if not result.returncode else'fail','production_ROM_sha256':digest,'skip_common_regression':args.new_only,'skip_whole_music':args.skip_music,'tests':rows};(out/'progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(rows[-1],ensure_ascii=False),flush=True)
        if result.returncode:raise SystemExit(result.returncode)
    report['status']='partial_checks_pass'if args.skip_music else'pass';(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    if not args.skip_music:
        from collect_balanced_acceptance import collect
        collect()
    print(json.dumps({k:v for k,v in report.items()if k!='tests'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
