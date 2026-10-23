"""Stage matching ordinary and acceptance sources, preserving prior releases."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
from project_env import ROOT,arm_prefix
from deliver_optimization import inputs

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 out=ROOT/'evidence/animation_smooth_20261023';baseline=json.loads((ROOT/'evidence/animation_optimization_20261023/delivery.json').read_text());archive=Path(baseline['SOURCE_ZIP']);assert sha(archive)==baseline['source_ZIP_sha256']
 if '--reuse' in sys.argv and(out/'staging.json').exists():
  old_state=json.loads((out/'staging.json').read_text());stage=Path(old_state['stage']);project=Path(old_state['project'])
 else:
  stage=Path(tempfile.mkdtemp(prefix='ruina-animation-v074-',dir='/tmp'));project=stage/'废都物语_GBA_匹配工程_v0.7.4_20261023'
  with zipfile.ZipFile(archive)as z:
   roots={Path(n).parts[0]for n in z.namelist()};assert len(roots)==1
   z.extractall(stage);(stage/next(iter(roots))).rename(project)
 selected=inputs()+[Path('README.md')]+[Path('build')/p for p in ('battle_animation_assets.h','battle_animations.bin','battle_animation_manifest.json','portraits_packed.bin')]
 for p in sorted(set(selected)):
  if not(ROOT/p).is_file():continue
  target=project/p;target.parent.mkdir(parents=True,exist_ok=True)
  if not target.exists()or sha(target)!=sha(ROOT/p):shutil.copy2(ROOT/p,target)
 env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_v074_original.zip',RUINA_FONT='/nonexistent_v074_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_v074_image_python')
 with(out/'source_rebuild.log').open('w')as stream:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
 ordinary=project/'build/废都物语_GBA_开篇开发验证版.gba';production=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';assert sha(ordinary)==sha(production)
 boost=stage/'废都物语_GBA_验收增强工程_v0.7.4_20261023';shutil.copytree(project,boost,dirs_exist_ok=True)
 old=Path(json.loads((ROOT/'evidence/acceptance_boost_20261023/build.json').read_text())['project'])
 for name in ('acceptance_boost.c','game.c','game.h','ruina_adapter.c'):shutil.copy2(old/'source'/name,boost/'source'/name)
 p=boost/'source/maps.c';p.write_text((project/'source/maps.c').read_text().replace('void map_screen(void){world_screen();}','void map_screen(void){acceptance_boost_prepare();world_screen();}').replace('队伍状态 · 原始数值','队伍状态 · 验收版'))
 p=boost/'tools/build.py';s=p.read_text().replace("b'RUBA'","b'RUAA'").replace("report['version']='0.7.4'","report['version']='0.7.4-acceptance'");p.write_text(s)
 with(out/'acceptance_build.log').open('w')as stream:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=boost,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
 boosted=boost/'build/废都物语_GBA_开篇开发验证版.gba'
 report={'status':'built_not_delivered','stage':str(stage),'project':str(project),'acceptance_project':str(boost),'ROM':str(ordinary),'ROM_sha256':sha(ordinary),'acceptance_ROM':str(boosted),'acceptance_ROM_sha256':sha(boosted),'formal_source_rebuild_byte_identical':True,'original_archive_and_font_disabled_for_rebuild':True,'physical_hardware':'not_run','full_campaign':'not_run'}
 (out/'staging.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
