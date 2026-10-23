"""Compare original full shop to the current representation and partial UI."""
import hashlib,json,subprocess,sys
from project_env import ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    digest=sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba');out=ROOT/'evidence/balanced_optimization_20261023/shop_comparison'/digest[:12];out.mkdir(parents=True,exist_ok=True);reports=[]
    for label,source,args in [('full','tests/shop_full_reference.c',['--face','--shop','tests/shop_full_reference.c']),('current','runtime/rm2k/shop.c',['--face'])]:
        with(out/(label+'.log')).open('w')as stream:subprocess.run([sys.executable,'tools/check_shop_stack.py',*args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
        matches=[]
        for p in(ROOT/'evidence/balanced_optimization_20261023/shop_stack'/digest[:12]).glob('*/result.json'):
            d=json.loads(p.read_text())
            if d.get('shop_source_sha256')==sha(ROOT/source)and d.get('portrait_in_description')and d.get('initial_gold')==12345 and d.get('test_fixture_source_sha256')==sha(ROOT/'tests/shop_stack_gba.c'):matches.append((p,d))
        assert matches,(label,'no matching source-bound result');reports.append(max(matches,key=lambda r:r[0].stat().st_mtime_ns))
    (a,old),(b,new)=reports;assert old['transaction']==new['transaction'];assert new['transaction']['gold_before']==12345 and new['transaction']['gold_after']==17295
    checks=[]
    for p in sorted(a.parent.glob('*.png')):
        q=b.parent/p.name;assert q.exists()and p.read_bytes()==q.read_bytes(),('different shop pixels',p.name);checks.append(p.name)
    assert len(checks)>=10
    result={'status':'pass','production_ROM_sha256':digest,'shop_source_sha256':sha(ROOT/'runtime/rm2k/shop.c'),'item_mask_header_sha256':sha(ROOT/'runtime/rm2k/item_mask.h'),'full_reference_report':str(a.relative_to(ROOT)),'current_report':str(b.relative_to(ROOT)),'LCD_screens_exact':checks,'transaction':new['transaction'],'old_response':old['input_response'],'current_response':new['input_response'],'minimum_SYS_margin_before':min(r['SYS_margin_above_fast_code_data']for r in old['observations']),'minimum_SYS_margin_after':min(r['SYS_margin_above_fast_code_data']for r in new['observations']),'scope':'Separate source-bound real-GBA fixtures with original item DB, actual event VM and buttons. Exact shop/list/quantity pixels and identical full Game after sale of99 items, stock exhaustion/reopen and refused buy at capacity. No natural-campaign claim.','hardware':'not_run'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
