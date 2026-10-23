"""Verify original payload identity and unchanged combat rule function bodies."""
import hashlib,json,re
from project_env import ROOT
BASE=ROOT/'evidence/balanced_optimization_20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def body(text,name):
    match=re.search(r'\b'+re.escape(name)+r'\([^;{}]*\)\s*\{',text);assert match,name
    start=match.start();at=match.end();depth=1
    while depth:
        if text[at]=='{':depth+=1
        if text[at]=='}':depth-=1
        at+=1
    return text[start:at]
def main():
    receipt=json.loads((ROOT/'build/build_receipt.json').read_text());baseline=json.loads((ROOT/'history/balanced_optimization_20261023/baseline/build/build_receipt.json').read_text());reference=json.loads((ROOT/'research/combat_rule_reference_40820.json').read_text());battle=(ROOT/'runtime/rm2k/battle.c').read_text()
    payloads=[]
    for path in ('build/original_lcf.bin','build/commands.bin','build/pages.bin','build/audio.bin','build/portraits.bin','build/portrait_combinations.bin','build/characters.bin','build/palette_lookup.bin','build/high_color_blobs.bin'):
        value=sha(ROOT/path);assert value==baseline['compiler_inputs_sha256'][path]==receipt['compiler_inputs_sha256'][path]
        payloads.append({'path':path,'SHA256':value,'same_as_v062':True})
    rules=[]
    for name,expected in reference['function_body_sha256'].items():
        value=hashlib.sha256(body(battle,name).encode()).hexdigest();assert value==expected,name
        rules.append({'function':name,'SHA256':value,'same_as_pre_UI_repair':True})
    runtime=[p for p in receipt['compiler_inputs_sha256']if p.startswith('runtime/')and p.endswith('.c')]
    result={'status':'pass','production_ROM_sha256':receipt['sha256'],'baseline_ROM_sha256':baseline['sha256'],'unchanged_payloads':payloads,'unchanged_runtime_sources':[p for p in runtime if receipt['compiler_inputs_sha256'][p]==baseline['compiler_inputs_sha256'].get(p)],'modified_runtime_sources':[p for p in runtime if receipt['compiler_inputs_sha256'][p]!=baseline['compiler_inputs_sha256'].get(p)],'unchanged_combat_rule_functions':rules,'combat_reference':reference['source_ROM_sha256'],'scope':'Byte identity of original game payloads; selected combat formula/AI functions also retain exact pre-menu-repair bodies. UI planning now supports nested cancellation, restores provisional RNG/actions, keeps cursor selection and reuses exact RGB555 background pixels. This is not complete RPG_RT or full-campaign equivalence.','attribution':'In-game production information page plus CREDITS.txt; title artwork unchanged as independently checked.'}
    (BASE/'content_identity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('unchanged_payloads','unchanged_combat_rule_functions')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
