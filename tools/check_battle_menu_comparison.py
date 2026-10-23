"""Compare exact battle menu pixels against complete background redraws."""
import hashlib,json,subprocess,sys
from project_env import ROOT

def main():
    digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest()
    base=ROOT/'evidence/balanced_optimization_20261023'/digest[:12]
    base.mkdir(parents=True,exist_ok=True)
    for label,args in [('current',[]),('full_reference',['--reference'])]:
        with(base/('battle_menu_'+label+'.log')).open('w')as stream:
            subprocess.run([sys.executable,'tools/check_battle_menu_navigation.py',*args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
    current=json.loads((base/'battle_menu_navigation/result.json').read_text());reference=json.loads((base/'battle_menu_navigation_full_reference/result.json').read_text())
    assert current['production_ROM_sha256']==reference['production_ROM_sha256']==digest
    assert current['status']==reference['status']=='pass'
    assert current['LCD_states']==reference['LCD_states']and len(current['LCD_states'])==48
    assert not current['music_underruns']and not reference['music_underruns']
    report={'status':'pass','production_ROM_sha256':digest,'LCD_states_exact':len(current['LCD_states']),'current_response':current['summary'],'full_reference_response':reference['summary'],'checks':current['checks'],'held_repeat':current['held_repeat'],'music_underruns':current['music_underruns'],'scope':'Original ordinary SAV, actual buttons and unchanged inventory/stats. A separately linked controlled reference redraws full battle/list backgrounds. Matching pixels do not imply full campaign or hardware acceptance.'}
    (base/'battle_menu_comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
