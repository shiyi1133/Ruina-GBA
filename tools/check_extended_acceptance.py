"""Broader genuine first encounters and recovery, plus isolated source menus.
The natural chapter run is checked separately and is never replaced by these
fixtures. Original battle outcomes come from actual button inputs and rules.
"""
import hashlib,json,subprocess,sys,time
from project_env import ROOT

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/extended_acceptance'/digest[:12];out.mkdir(parents=True,exist_ok=True);rows=[]
 cases=[(f'origin_{n}_manual',['tools/check_first_battle.py',str(n)],f'evidence/first_battle_origin_{n}/result.json')for n in range(1,5)]
 cases += [('mage_original_auto_battle',['tools/check_first_battle.py','3','--auto'],'evidence/first_battle_origin_3_auto/result.json'),('game_over_new_game_bad_SAV',['tools/check_recovery.py'],'evidence/recovery/result.json'),('source_interfaces_controlled',['tools/check_full_interfaces.py'],'evidence/full_features/interfaces/result.json')]
 for name,args,path in cases:
  started=time.monotonic()
  with(out/(name+'.log')).open('w')as stream:p=subprocess.run([sys.executable,*args],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  assert p.returncode==0,(name,p.returncode,str(out/(name+'.log')))
  r=json.loads((ROOT/path).read_text());assert r['status']=='pass'and r.get('rom_sha256',r.get('release_rom_sha256'))==digest
  rows.append({'name':name,'status':'pass','report':path,'seconds':time.monotonic()-started});print(json.dumps(rows[-1]),flush=True)
 assert hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest()==digest
 result={'status':'pass','production_rom_sha256':digest,'checks':rows,'kind':'four fresh origins and original automatic mage battle, genuine SAV defeat/reset/rejection; special interfaces use separate controlled cartridge','full_campaign':'not_run','hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
