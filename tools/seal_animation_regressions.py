"""Tie image, menu and save-adjacent regression results to this exact ROM."""
import hashlib,json
from pathlib import Path
from project_env import ROOT
def read(p):return json.loads(p.read_text())
def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();out=ROOT/'evidence/animation_optimization_20261023'
 rgb=[p for p in (ROOT/'evidence/balanced_optimization_20261023/rgb_pixels').glob('*/result.json') if read(p).get('production_baseline_SHA256')==digest];assert len(rgb)==1
 portrait=ROOT/read(ROOT/'evidence/optimization_20261022/portrait_matrix/latest_stress_subset_attempt.json')['report']
 refs=rgb+[portrait,ROOT/f'evidence/balanced_optimization_20261023/{digest[:12]}/battle_menu_navigation/result.json',ROOT/'evidence/hardware_scroll/native_crop/result.json']
 rows=[]
 for p in refs:
  result=read(p);assert result['status']=='pass',p
  actual=next(result[k]for k in ('production_ROM_sha256','production_rom_sha256','production_baseline_SHA256')if k in result);assert actual==digest,(p,actual)
  rows.append({'report':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'status':'pass'})
 host=ROOT/'evidence/optimization_20261022/art/tiled_codec_host.json';result=read(host);assert result['status']=='pass'and result['block_indexed_spans']>1000
 for p,h in result['sources'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
 rows.append({'report':str(host.relative_to(ROOT)),'sha256':hashlib.sha256(host.read_bytes()).hexdigest(),'status':'pass','source_hashes_match':True})
 result={'status':'pass','production_ROM_sha256':digest,'reports':rows,'scope':'44 independent LCD RGB555 cases; 164 original/mixed portrait faces with music and four effects; actual legacy battle menus and B cancellation; native-map controlled palette crop; random clipped block/tile decoder spans with interleaved shared-workspace use. See each report for its scope and video override.'}
 (out/'regression_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
