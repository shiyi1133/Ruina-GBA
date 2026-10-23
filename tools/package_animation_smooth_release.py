"""Seal the tested v0.7.4 pair and independently rebuild its shipped source ZIP."""
import hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from pathlib import Path
from project_env import ROOT,arm_prefix
from deliver_optimization import inputs
OUT=ROOT/'evidence/animation_smooth_20261023'
VERSION='0.7.4'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2))
def actual(p):p=Path(p);return p if p.is_absolute()else ROOT/p
def reference(p):return actual(read(ROOT/p)['report'])
def report_digest(r):return next((r[k]for k in('production_ROM_sha256','production_rom_sha256','production_baseline_SHA256','rom_sha256','ROM_sha256')if k in r),None)
def copy(p,d):d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
def main():
 state=read(OUT/'staging.json');project=Path(state['project']);boost=Path(state['acceptance_project']);rom=Path(state['ROM']);enhanced=Path(state['acceptance_ROM']);digest=sha(rom)
 assert digest==state['ROM_sha256']==sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba')
 assert sha(enhanced)==state['acceptance_ROM_sha256']
 refs=[reference('evidence/battle_animations_20261023/gallery_latest.json'),reference('evidence/battle_animations_20261023/targets_latest.json'),reference('evidence/animation_optimization_20261023/blend_latest.json'),reference('evidence/optimization_20261022/portrait_matrix/latest_stress_subset_attempt.json'),reference('evidence/optimization_20261022/music/gba_matrix/latest_attempt.json')]
 refs += [OUT/p for p in('sequences_release_all.json','timing_all.json','cache_reuse.json','settings.json','settings_glyphs.json','cadence_release_v074.json','cadence_release_full_v074.json')]
 refs += [ROOT/'evidence/first_battle_origin_3/result.json',ROOT/f'evidence/balanced_optimization_20261023/save_stack/{digest[:12]}/result.json',ROOT/f'evidence/balanced_optimization_20261023/{digest[:12]}/battle_menu_navigation/result.json',ROOT/f'evidence/balanced_optimization_20261023/{digest[:12]}/performance_release_v074/result.json',ROOT/'evidence/hardware_scroll/native_crop/result.json']
 rgb=[p for p in(ROOT/'evidence/balanced_optimization_20261023/rgb_pixels').glob('*/result.json')if report_digest(read(p))==digest and read(p).get('extra_native')];assert len(rgb)==1;refs+=rgb
 for p in refs:
  r=read(p);assert report_digest(r)==digest,(p,report_digest(r))
  if r['status']=='measured':assert r['sample_count']==60 and all(s['black_frames']==0 for s in r['summary']),p
  else:assert r['status']=='pass',(p,r.get('status'))
 seq=read(OUT/'sequences_release_all.json');assert seq['animation_records']==230 and seq['source_frames']==4501 and seq['all_LCD_pixels_identical']
 timing=read(OUT/'timing_all.json');assert timing['animation_records']==230 and timing['playback_modes']==2 and len(timing['cases'])==460
 assert timing['all_original_timing_events_in_order_once']and timing['clean_restoration_after_every_case']and timing['no_MIDI_queue_underruns']
 assert len(read(rgb[0])['checks'])==44
 music=read(refs[4]);assert len(music['cases'])==198 and all(r['status']=='pass'for r in music['cases'])
 playback=read(ROOT/'evidence/animation_optimization_20261023/playback_release_v074.json');complete=read(ROOT/'evidence/animation_optimization_20261023/playback_release_full_v074.json')
 for r in(playback,complete):assert r['status']=='pass'and r['production_ROM_sha256']==digest and all(s['MIDI_underruns']==0 for s in r['samples'])
 refs += [ROOT/'evidence/animation_optimization_20261023/playback_release_v074.json',ROOT/'evidence/animation_optimization_20261023/playback_release_full_v074.json']
 receipt=read(ROOT/'build/build_receipt.json');assert receipt['sha256']==digest and all(sha(ROOT/p)==h for p,h in receipt['compiler_inputs_sha256'].items())
 host=read(ROOT/'evidence/optimization_20261022/art/tiled_codec_host.json');assert host['status']=='pass'and all(sha(ROOT/p)==h for p,h in host['sources'].items());refs.append(ROOT/'evidence/optimization_20261022/art/tiled_codec_host.json')
 accepted=read(project/read(project/'evidence/acceptance_boost_20261023/validation.json')['report']);assert accepted['status']=='pass'and accepted['ROM_sha256']==sha(enhanced)
 validation={'status':'pass','version':VERSION,'ROM_sha256':digest,'acceptance_ROM_sha256':sha(enhanced),'reports':[str(p.relative_to(ROOT))for p in refs],'original_time_playback':playback,'complete_frames_playback':complete,'all_original_frame_LCD_comparison':{k:v for k,v in seq.items()if k!='frames'},'timing_events':{k:v for k,v in timing.items()if k!='cases'},'acceptance_checks':accepted['checks'],'source_folder_rebuild_byte_identical':True,'source_ZIP_rebuild':'pending','scope':'230 original records, 4501 individual source frames compared on actual LCD in the paused complete-frame fixture; 460 live MIDI/SFX playback cases verify both modes and ordered timing events. 44 independent RGB555 cases, all integer opacity percentages, 164 face/mixed palette samples under audio stress, ordinary save/cold-load and stack observations, real first victory, actual skill targeting and menu cancellation. All 99 MIDI scores sampled for 3 seconds near each mode polyphony peak. Enhancement checked for all four origins, 65 enabled magic spells, actual cast and save.','limitations':['Original-time mode deliberately omits late transition frames; it does not guarantee 30 FPS or exact PC presentation speed.','Complete-frames mode retains all pictures and can still run slowly on very complex effects.','Music checks are peak spot checks, not all complete scores on GBA.','Map event animation, shake and black scene cuts retain existing reduced presentation.'],'physical_hardware':'not_run','full_campaign':'not_run'}
 write(OUT/'validation.json',validation)
 for p in sorted(set(inputs()+[Path('README.md')]+[Path('build')/p for p in('battle_animation_assets.h','battle_animations.bin','battle_animation_manifest.json','portraits_packed.bin')])):
  if(ROOT/p).is_file():copy(ROOT/p,project/p)
 for p in OUT.rglob('*'):
  if p.is_file()and p.suffix in('.json','.png','.txt','.log')and not any(q in('baseline','before_overlay','before_native_index','rejected_native_index','rejected_coverage')for q in p.parts):copy(p,project/p.relative_to(ROOT))
 for p in refs:copy(p,project/p.relative_to(ROOT))
 write(project/'evidence/animation_smooth_20261023/acceptance_validation.json',{k:v for k,v in accepted.items()if k!='commands'})
 for name in('acceptance_boost.c','game.c','game.h','maps.c','ruina_adapter.c'):copy(boost/'source'/name,project/'variants/acceptance/source'/name)
 copy(boost/'tools/build.py',project/'variants/acceptance/tools/build.py')
 write(project/'variants/acceptance/variant.json',{'version':'0.7.4-acceptance','ROM_sha256':sha(enhanced),'application':'Replace same relative source/ and tools/ files in a separate project copy, then build --incremental.','HP_MP_and_bonuses':999,'magic_spells':65,'all_learnable_abilities':194,'boost_trigger':'once after original character creation; never on ordinary save load'})
 (project/'工程使用说明.txt').write_text('''匹配工程 v0.7.4（2026-10-23）
设置 ARM_TOOLCHAIN_PREFIX 指向 GNU Arm Embedded 工具链，再执行 python3 tools/build.py --incremental。
已转换资源随工程提供，增量重建不需要原 ZIP、字体或图像库。
普通版源码位于 source/、runtime/、platform/；验收增强修改在 variants/acceptance/。
请在独立副本覆盖增强版同名 source/、tools/ 文件，再构建。
默认原速计时，复杂过渡画面可能略过。B 菜单 → 动画播放 → 完整播放，保留全部画面但可能较慢。
完整通关、全部结局和实机未验收。当前范围、散列及保留的未通过尝试见 evidence/animation_smooth_20261023/。
''',encoding='utf-8-sig')
 blocked={'.gba','.elf','.o','.map','.exe','.dll','.so','.pyc'};files=[p for p in project.rglob('*')if p.is_file()and'.git'not in p.parts and'__pycache__'not in p.parts and p.suffix.lower()not in blocked and p.name not in('工程文件清单.json','gba_acceptance_probe')and'/build/fixtures/'not in str(p)]
 inventory={'version':VERSION,'ROM_sha256':digest,'acceptance_ROM_sha256':sha(enhanced),'files':[{'path':str(p.relative_to(project)),'bytes':p.stat().st_size,'sha256':sha(p)}for p in sorted(files)]};write(project/'工程文件清单.json',inventory);files.append(project/'工程文件清单.json')
 downloads=Path('/mnt/c/Users/APP/Downloads');source_zip=downloads/'废都物语_GBA_匹配工程_v0.7.4_20261023.zip';assert not source_zip.exists()
 with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(files):
   info=zipfile.ZipInfo(str(Path(project.name)/p.relative_to(project)));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,p.read_bytes())
 fresh=Path(tempfile.mkdtemp(prefix='ruina-v074-zip-proof-',dir='/tmp'))
 with zipfile.ZipFile(source_zip)as z:assert z.testzip()is None;z.extractall(fresh)
 rebuilt=fresh/project.name
 for row in inventory['files']:assert sha(rebuilt/row['path'])==row['sha256'],row['path']
 env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_v074_original.zip',RUINA_FONT='/nonexistent_v074_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_v074_image_python')
 for mode in('ordinary','acceptance'):
  if mode=='acceptance':
   for folder in('source','tools'):
    for p in(rebuilt/'variants/acceptance'/folder).glob('*'):
     if p.is_file():copy(p,rebuilt/folder/p.name)
  with(OUT/('actual_ZIP_'+mode+'_rebuild.log')).open('w')as stream:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=rebuilt,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
  assert sha(rebuilt/'build/废都物语_GBA_开篇开发验证版.gba')==(digest if mode=='ordinary'else sha(enhanced))
 proof={'status':'pass','ROM_sha256':digest,'acceptance_ROM_sha256':sha(enhanced),'source_ZIP':str(source_zip),'source_ZIP_sha256':sha(source_zip),'fresh_project':str(rebuilt),'original_archive_font_image_python':'disabled','python_site_packages':'disabled by -S','both_rebuilds_byte_identical':True};write(OUT/'actual_ZIP_rebuild.json',proof);validation['source_ZIP_rebuild']='pass, both byte identical';write(OUT/'validation.json',validation)
 demo=downloads/'废都物语_GBA_v0.7.4_动画播放优化版_20261023';demo.mkdir(exist_ok=False);regular=demo/'废都物语_GBA_v0.7.4_普通版.gba';test=demo/'废都物语_GBA_v0.7.4_验收增强版.gba';copy(rom,regular);copy(enhanced,test)
 (demo/'使用说明.txt').write_text('''v0.7.4 动画播放优化
普通版：原始数值，可继续游玩。
验收增强版：新游戏创建人物后 HP/MP 与基础属性 999，学会 65 个魔法及可学能力；旧普通存档保持原数值。
默认“原速播放”按原时长推进，来不及绘制的过渡画面可能略过，原定时音效依次处理。
B 菜单 → 动画播放 → 完整播放：保留全部画面，但复杂技能会放慢。本次运行有效。
游戏音乐进一步简化采样，欣赏模式保留原有细致档。技能效果、数值及普通 SAV 格式不变。
旧 SAV 请先备份，再复制为新 ROM 的同名 .sav；不要沿用模拟器即时存档。
已检查全部 230 个动画的两种播放方式、4501 个原始帧的画面、菜单返回、首战及普通存档。
完整通关和实机未验收，重特效不保证 30 FPS。匹配工程和验证范围随包提供。
''',encoding='utf-8-sig');copy(OUT/'validation.json',demo/'验证范围.json');copy(OUT/'actual_ZIP_rebuild.json',demo/'工程重建核对.json')
 demo_zip=downloads/(demo.name+'.zip')
 with zipfile.ZipFile(demo_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(demo.rglob('*')):
   if p.is_file():z.write(p,Path(demo.name)/p.relative_to(demo))
 combined=downloads/'废都物语_GBA_v0.7.4_工程与试玩ROM_20261023.zip';assert not combined.exists()
 with zipfile.ZipFile(combined,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for archive,prefix in((source_zip,'工程'),(demo_zip,'试玩')):
   with zipfile.ZipFile(archive)as source:
    for name in source.namelist():
     if not name.endswith('/'):z.writestr(str(Path(prefix)/Path(*Path(name).parts[1:])),source.read(name))
 for p in(source_zip,demo_zip,combined):
  with zipfile.ZipFile(p)as z:assert z.testzip()is None
 with zipfile.ZipFile(combined)as z:
  assert hashlib.sha256(z.read('试玩/'+regular.name)).hexdigest()==digest
  assert hashlib.sha256(z.read('试玩/'+test.name)).hexdigest()==sha(enhanced)
 result={'status':'delivered','version':VERSION,'ROM':str(regular),'ROM_sha256':digest,'acceptance_ROM':str(test),'acceptance_ROM_sha256':sha(enhanced),'SOURCE_ZIP':str(source_zip),'source_ZIP_sha256':sha(source_zip),'DEMO_ZIP':str(demo_zip),'demo_ZIP_sha256':sha(demo_zip),'COMBINED_ZIP':str(combined),'combined_ZIP_sha256':sha(combined),'source_ZIP_rebuild_byte_identical':True,'project':str(project),'fresh_ZIP_project':str(rebuilt),'physical_hardware':'not_run','full_campaign':'not_run'};write(OUT/'delivery.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
