"""Seal v0.7.3 source and both playable variants after scoped QA passes."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
from project_env import ROOT,arm_prefix
from deliver_optimization import inputs
OUT=ROOT/'evidence/animation_optimization_20261023'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2))
def main():
 state=read(OUT/'staging.json');project=Path(state['project']);boost=Path(state['acceptance_project']);rom=Path(state['ROM']);enhanced=Path(state['acceptance_ROM']);digest=sha(rom);assert digest==sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba')==state['ROM_sha256']
 reports=[Path(read(ROOT/'evidence/battle_animations_20261023'/p)['report'])for p in ('gallery_latest.json','targets_latest.json')]+[Path(read(OUT/'blend_latest.json')['report'])]
 reports += [ROOT/'evidence/first_battle_origin_3/result.json',ROOT/f'evidence/balanced_optimization_20261023/save_stack/{digest[:12]}/result.json',OUT/'regression_summary.json']
 for p in reports:
  r=read(p);assert r['status']=='pass'and(r.get('production_ROM_sha256')or r.get('rom_sha256'))==digest,p
 comparison=read(OUT/('comparison_'+digest[:12]+'.json'));playback=read(OUT/'playback_final.json');baseline=read(OUT/'playback_baseline.json')
 assert comparison['status']=='pass'and comparison['candidate_ROM']==digest and comparison['LCD_pixels_identical']and comparison['frames_compared']==213
 assert playback['status']=='pass'and playback['production_ROM_sha256']==digest and len(playback['samples'])==4 and all(r['MIDI_underruns']==0 for r in playback['samples'])and playback['total_seconds']<baseline['total_seconds']
 inputs_receipt=read(ROOT/'build/build_receipt.json');assert all(sha(ROOT/p)==h for p,h in inputs_receipt['compiler_inputs_sha256'].items())
 acceptance_ref=read(project/'evidence/acceptance_boost_20261023/validation.json');acceptance_report=read(project/acceptance_ref['report']);assert acceptance_report['status']=='pass'and acceptance_report['ROM_sha256']==sha(enhanced)==state['acceptance_ROM_sha256']
 validation={'status':'pass','version':'0.7.3','ROM_sha256':digest,'acceptance_ROM_sha256':sha(enhanced),'reports':[str(p.relative_to(ROOT))for p in reports],'storage':read(ROOT/'evidence/battle_animations_20261023/storage.json'),'non_face_storage':read(ROOT/'evidence/battle_animations_20261023/compaction.json'),'render_comparison':read(OUT/('comparison_'+digest[:12]+'.json')),'complete_playback':read(OUT/'playback_final.json'),'acceptance_checks':acceptance_report['checks'],'source_folder_rebuild_byte_identical':True,'source_ZIP_rebuild':'pending','scope':'213 visual animation records sampled on actual LCD and restored cleanly; independent original XYZ verification of all 601 referenced cells (600 visible), 160 losslessly packed portraits; actual production skill targeting for healing, single enemy, three enemies and self; real new-game first victory; ordinary SRAM save/cold-load; four origins at high stats and 65 magic spells enabled in acceptance build. Current-build image regression covers every integer cell opacity, scaled-image shared-workspace invalidation, 44 independent RGB555 cases, 164 original/mixed faces under audio stress and real battle-menu navigation; native crop uses its documented controlled video override.','limitations':['Complex effects can be substantially slower than PC; no PC-speed or 30-fps claim.','Map event animation and map shake retain existing reduced presentation.'],'physical_hardware':'not_run','full_campaign':'not_run'}
 write(OUT/'validation.json',validation)
 selected=inputs()+[Path('README.md')]+[Path('build')/p for p in ('battle_animation_assets.h','battle_animations.bin','battle_animation_manifest.json','portraits_packed.bin')]
 for p in sorted(set(selected)):
  if (ROOT/p).is_file():
   dest=project/p;dest.parent.mkdir(parents=True,exist_ok=True)
   if not dest.exists()or sha(dest)!=sha(ROOT/p):shutil.copy2(ROOT/p,dest)
 for p in OUT.rglob('*'):
  if p.is_file()and p.suffix in('.json','.png','.log','.txt','.gif')and 'baseline'not in p.parts and not p.name.startswith(('source_rebuild','acceptance_build','build')):
   dest=project/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 for p in reports:
  dest=project/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 for row in read(OUT/'regression_summary.json')['reports']:
  p=ROOT/row['report'];assert sha(p)==row['sha256'];dest=project/row['report'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 write(project/'evidence/animation_optimization_20261023/acceptance_validation.json',{k:v for k,v in acceptance_report.items()if k!='commands'})
 # The accepted source changes are kept beside the ordinary engine for reuse.
 for name in ('acceptance_boost.c','game.c','game.h','maps.c','ruina_adapter.c'):
  dest=project/'variants/acceptance/source'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(boost/'source'/name,dest)
 dest=project/'variants/acceptance/tools/build.py';dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(boost/'tools/build.py',dest)
 write(project/'variants/acceptance/variant.json',{'version':'0.7.3-acceptance','ROM_sha256':sha(enhanced),'application':'Replace same relative source/ and tools/ files with this variant, then build --incremental. Use a separate copy of the project.','HP_MP_and_bonuses':999,'magic_spells':65,'all_learnable_abilities':194,'boost_trigger':'once after original character creation; never on ordinary save load'})
 (project/'工程使用说明.txt').write_text('''匹配工程 v0.7.3：优化战斗动画（2026-10-23）

使用外部 GNU Arm Embedded 工具链，执行 python3 tools/build.py --incremental。
已转换资源随工程提供，增量重建不需要原始 ZIP、字体或图像库。
此工程是普通数值版。验收增强版修改位于 variants/acceptance/：
在独立副本中覆盖其中同名 source/ 和 tools/ 文件，再增量构建。
恢复的是战斗逐帧图案。地图转场仍直接切黑；复杂战斗特效可能显著慢于 PC。
当前验证范围与每个版本的 SHA-256 见 evidence/animation_optimization_20261023/。
完整自然通关、全部结局与实机未验收。旧版本、旧存档和失败证据保留。
''',encoding='utf-8-sig')
 blocked={'.gba','.elf','.o','.map','.exe','.dll','.so','.pyc'}
 files=[p for p in project.rglob('*')if p.is_file()and'.git'not in p.parts and'__pycache__'not in p.parts and p.suffix.lower()not in blocked and p.name not in('工程文件清单.json','gba_acceptance_probe')and'/build/fixtures/'not in str(p)]
 inventory={'version':'0.7.3','ROM_sha256':digest,'acceptance_ROM_sha256':sha(enhanced),'files':[{'path':str(p.relative_to(project)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(files)]};write(project/'工程文件清单.json',inventory);files.append(project/'工程文件清单.json')
 downloads=Path('/mnt/c/Users/APP/Downloads');source_zip=downloads/'废都物语_GBA_匹配工程_v0.7.3_20261023.zip';assert not source_zip.exists()
 with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(files):
   info=zipfile.ZipInfo(str(Path(project.name)/p.relative_to(project)));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,p.read_bytes())
 # Verify the actual shipped ZIP in a new folder with original inputs disabled.
 fresh=Path(tempfile.mkdtemp(prefix='ruina-v073-zip-proof-',dir='/tmp'))
 with zipfile.ZipFile(source_zip)as z:assert z.testzip()is None;z.extractall(fresh)
 rebuilt=fresh/project.name
 for row in inventory['files']:assert sha(rebuilt/row['path'])==row['sha256'],row['path']
 env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_v073_original.zip',RUINA_FONT='/nonexistent_v073_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_v073_image_python')
 with(OUT/'actual_ZIP_rebuild.log').open('w')as stream:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=rebuilt,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
 assert sha(rebuilt/'build/废都物语_GBA_开篇开发验证版.gba')==digest
 # Rebuild the acceptance variant from the same actual ZIP's bundled overrides.
 for folder in ('source','tools'):
  for p in (rebuilt/'variants/acceptance'/folder).glob('*'):
   if p.is_file():shutil.copy2(p,rebuilt/folder/p.name)
 with(OUT/'actual_acceptance_ZIP_rebuild.log').open('w')as stream:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=rebuilt,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
 assert sha(rebuilt/'build/废都物语_GBA_开篇开发验证版.gba')==sha(enhanced)
 write(OUT/'actual_ZIP_rebuild.json',{'status':'pass','acceptance_ROM_sha256':sha(enhanced),'bundled_acceptance_variant_rebuild':'pass, byte identical','ROM_sha256':digest,'source_ZIP':str(source_zip),'source_ZIP_sha256':sha(source_zip),'fresh_project':str(rebuilt),'original_archive_font_and_image_python':'disabled','python_site_packages':'disabled by -S'})
 validation['source_ZIP_rebuild']='pass, byte identical';write(OUT/'validation.json',validation)
 demo=downloads/'废都物语_GBA_v0.7.3_战斗动画优化版_20261023';demo.mkdir(exist_ok=False)
 regular=demo/'废都物语_GBA_v0.7.3_普通版.gba';test=demo/'废都物语_GBA_v0.7.3_验收增强版.gba';shutil.copy2(rom,regular);shutil.copy2(enhanced,test)
 (demo/'使用说明.txt').write_text('''v0.7.3 战斗动画优化版

普通版：原始数值，可继续游玩。
验收增强版：新游戏后 HP/MP 与基础属性 999，学会原版 65 个魔法和可学能力，配备合法魔法武器。
旧普通存档读取后维持原数值；要体验增强效果，请开始新游戏。
两版均保留原数据的攻击、治疗、范围和自身技能图案、帧序、透明度、色调与定时音效。
同样的213个抽查帧逐像素一致，平均绘制耗时约减少37%；四段完整播放合计约减少14%。
复杂样例从约25.8秒降到20.5秒；仍非PC原版速度。
复杂大特效仍可能明显慢于 PC；地图动画、震动和黑屏转场继续沿用之前的简化。
普通 SAV 可读写；不要混用模拟器即时存档，保留自己的原文件和存档。
已抽查首战、技能目标、画面恢复、四种出身及普通存档。完整通关和实机未验收。
匹配工程另见同版本工程 ZIP；variants/acceptance 内含增强版修改。
''',encoding='utf-8-sig')
 shutil.copy2(OUT/'validation.json',demo/'验证范围.json');shutil.copy2(OUT/'actual_ZIP_rebuild.json',demo/'工程重建核对.json')
 target_dir=Path(read(ROOT/'evidence/battle_animations_20261023/targets_latest.json')['report']).parent
 for name in ('stage1_frame10.png','stage2_frame12.png','stage3_frame12.png'):
  if(target_dir/name).exists():shutil.copy2(target_dir/name,demo/name)
 demo_zip=downloads/(demo.name+'.zip')
 with zipfile.ZipFile(demo_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(demo.rglob('*')):
   if p.is_file():z.write(p,Path(demo.name)/p.relative_to(demo))
 for p in(source_zip,demo_zip):
  with zipfile.ZipFile(p)as z:assert z.testzip()is None
 result={'status':'delivered','version':'0.7.3','ROM':str(regular),'ROM_sha256':digest,'acceptance_ROM':str(test),'acceptance_ROM_sha256':sha(enhanced),'SOURCE_ZIP':str(source_zip),'source_ZIP_sha256':sha(source_zip),'DEMO_ZIP':str(demo_zip),'demo_ZIP_sha256':sha(demo_zip),'source_ZIP_rebuild_byte_identical':True,'project':str(project),'fresh_ZIP_project':str(rebuilt),'physical_hardware':'not_run','full_campaign':'not_run'}
 write(OUT/'delivery.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
