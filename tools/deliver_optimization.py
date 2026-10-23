"""Prepare a clean source rebuild, seal verified artifacts, then deliver.
The six-hour user-requested optimization window is enforced only at delivery.
Preparing and verification happen beforehand; earlier releases are immutable.
"""
import argparse,datetime,hashlib,json,os,shutil,subprocess,sys,time,zipfile
from pathlib import Path
from project_env import ROOT,arm_prefix

VERSION='0.6';DATE='20261022'
STATE=ROOT/'evidence/optimization_20261022/release_preparation.json'
ROM=ROOT/'build/废都物语_GBA_开篇开发验证版.gba'
DEMO_NAME=f'废都物语_GBA_DEMO_v{VERSION}_画质性能版_{DATE}'
SOURCE_NAME=f'废都物语_GBA_匹配工程_v{VERSION}_{DATE}'
ROM_NAME=f'废都物语_GBA_v{VERSION}_画质性能版.gba'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def cp(source,target):
 target.parent.mkdir(parents=True,exist_ok=True)
 if not target.exists()or sha(source)!=sha(target):shutil.copy2(source,target)
def current():
 digest=sha(ROM);receipt=read('build/build_receipt.json');assert receipt['sha256']==digest and ROM.stat().st_size<=33554432
 assert all(sha(ROOT/p)==h for p,h in receipt['compiler_inputs_sha256'].items())
 regression=read(read('evidence/optimization_20261022/final_validation/latest_attempt.json')['report']);assert regression['status']=='pass'and regression['rom_sha256']==digest and regression['completed']==regression['total']
 return digest,receipt,regression
def inputs():
 selected=[]
 for directory in('source','runtime','platform','tools','tests','third_party','research/reference'):
  selected += [p.relative_to(ROOT)for p in(ROOT/directory).rglob('*')if p.is_file()and'__pycache__'not in p.parts]
 for pattern in('*.json','map_*.txt'):
  selected += [p.relative_to(ROOT)for p in(ROOT/'research').glob(pattern)]
 selected += [Path(p)for p in('README.txt','ARCHITECTURE.txt','CREDITS.txt','LICENSE','动画简化说明.txt','原尺寸地图说明.txt','移植约定.json')]
 cached=('assets.c','assets.h','asset_manifest.json','original_lcf.bin','audio.bin','audio_manifest.json','portraits.bin','portraits_manifest.json','portrait_combinations.bin','portrait_combinations_manifest.json','characters.bin','characters_manifest.json','commands.bin','commands_manifest.json','pages.bin','pages_manifest.json','borrowed_commands.c','borrowed_commands_manifest.json','palette_lookup.bin','palette_lookup_manifest.json','high_color_blobs.s','high_color_blobs.bin','high_color_manifest.json','native_soundfont_metadata.json','build_receipt.json')
 selected += [Path('build')/p for p in cached if(ROOT/'build'/p).exists()]
 selected += [p.relative_to(ROOT)for p in(ROOT/'build').glob('*_palette.png')]
 selected += [p.relative_to(ROOT)for p in(ROOT/'build/original').glob('*')if p.is_file()]
 selected += [p.relative_to(ROOT)for p in(ROOT/'build/audio_cache').glob('*.mid')]
 selected += [Path('build/native_music')/p for p in('native_soundfont.bin','manifest.json')]
 selected += [p.relative_to(ROOT)for p in(ROOT/'build/native_music').glob('*.events.json')]
 selected += [p.relative_to(ROOT)for p in(ROOT/'build/light_music').glob('*')if p.is_file()and p.suffix in('.json','.sequence','.bin')]
 selected += [Path('build/audio_source/easyrpg.soundfont')]
 selected += [Path(p)for p in('history/legacy_checkpoint_v2.sav','history/legacy_reentered_cave_v2.sav','evidence/save_cold_load/ordinary.sav')]
 selected += [p.relative_to(ROOT)for p in(ROOT/'evidence/chapter_progress').glob('*.sav')]
 return sorted(set(selected))
def evidence(project):
 # Retain the original scopes and rejected/not-run records, without copying
 # generated ROM fixtures or recordings into the matching source package.
 selected=[]
 for p in(ROOT/'evidence').rglob('*'):
  if p.is_file()and p.suffix in('.json','.txt','.log')and p!=STATE and'release_staging'not in p.parts:
   relative=p.relative_to(ROOT);cp(p,project/relative);selected.append(relative)
 return selected
def prepare():
 digest,receipt,regression=current();stage=ROOT/'build'/('release_staging_v06_'+digest[:12]);project=stage/SOURCE_NAME;project.mkdir(parents=True,exist_ok=True)
 selected=inputs();snapshot={str(p):sha(ROOT/p)for p in selected}
 for p in selected:cp(ROOT/p,project/p)
 env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_v06_original.zip',RUINA_FONT='/nonexistent_v06_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_v06_asset_python')
 started=time.monotonic()
 with(project/'工程重建日志.txt').open('w')as output:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=project,env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
 rebuilt=project/'build/废都物语_GBA_开篇开发验证版.gba';assert sha(rebuilt)==digest,'Matching source did not reproduce the playtested binary'
 check={'status':'pass','expected_rom_sha256':digest,'rebuilt_rom_sha256':sha(rebuilt),'original_archive_access':'disabled by nonexistent path','font_access':'disabled by nonexistent path','asset_python_access':'disabled by nonexistent path','python_site_packages':'disabled by -S','cached_incremental_build':True,'wall_seconds':time.monotonic()-started,'environment':'Linux/WSL with external GNU Arm toolchain; native Windows not tested','compiler_inputs_sha256':receipt['compiler_inputs_sha256']}
 write(project/'工程重建校验.json',check)
 assert all(sha(ROOT/p)==h and sha(project/p)==h for p,h in snapshot.items()),'A source input changed while preparing the matching project'
 state={'status':'prepared, not delivered','rom_sha256':digest,'stage':str(stage),'project':str(project),'selected_source':[str(p)for p in selected],'prepared_source_sha256':snapshot,'rebuild':check};write(STATE,state);print(json.dumps({k:v for k,v in state.items()if k not in('selected_source','prepared_source_sha256','rebuild')},ensure_ascii=False,indent=2))
def zipped(folder,paths):
 path=folder.parent/(folder.name+'.zip')
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(set(paths)):z.write(folder/p,Path(folder.name)/p)
 with zipfile.ZipFile(path)as z:assert z.testzip()is None
 return path
def seal():
 digest,receipt,regression=current();state=read(STATE);assert state['rom_sha256']==digest;project=Path(state['project']);stage=Path(state['stage'])
 # Compilation, generators and cached banks may not drift after clean rebuild.
 for p,h in state['prepared_source_sha256'].items():
  if p.startswith(('source/','runtime/','platform/','tools/','tests/','build/')):assert sha(ROOT/p)==h,('Source changed since prepare; prepare again',p)
 music=read(read('evidence/optimization_20261022/music/complete_GBA/latest_attempt.json')['report']);assert music['status']=='pass'and music['production_rom_sha256']==digest and music['completed']==music['total']==210
 selected=[Path(p)for p in state['selected_source']]
 for p in selected:cp(ROOT/p,project/p)
 selected+=evidence(project);selected += [Path('工程重建日志.txt'),Path('工程重建校验.json')]
 instructions='''匹配工程 v0.6（2026-10-22）

本包包含源码和转换资源，可在 Linux/WSL 安装 GNU Arm 工具链与 Python 3 后重建：
  python3 tools/build.py --incremental
可设置 ARM_TOOLCHAIN_PREFIX。重建不需要原 ZIP、系统字体或 Python 图像库。
工程重建校验.json 记录了关闭原包/字体访问、禁用 site packages 后的逐字节一致结果。

重新转换素材需要你自己的原游戏 ZIP、中文字体、Pillow 和 NumPy。
重新转换音乐可用 tools/rebuild_simplified_audio.py，输入缓存已附，需 NumPy。
当前两种模式均为简化音色，游戏中进一步简化；不用历史全音源实验来替换当前资源。
旧工具 deliver_demo、deliver_phase_demo、package_delivery 是历史发布流程；本版入口为 deliver_optimization。
本包不含 ROM、工具链、原游戏 ZIP、系统字体、旧版对比 ROM、所有生成的测试卡或录音。
build/ 下的 C/二进制缓存是可重建输入；history/、evidence/ 的 SAV 是测试材料，不要当作新游戏同名存档。

按键测试需自行提供 mGBA 开发库并构建 gba_acceptance_probe；设置 MGBA_PREFIX 可指定位置。
与原图逐像素比较的测试另需你自己的原 ZIP。历史性能对比需另外保留旧版 ROM/ELF；
没有旧版时回归脚本只测当前性能。完整自然通关、全部结局、实机仍未验收。
README.txt 介绍操作、当前验证范围与硬件差距；来源和许可证见 CREDITS.txt、LICENSE、third_party/。
'''
 (project/'工程使用说明.txt').write_text(instructions,encoding='utf-8-sig');selected.append(Path('工程使用说明.txt'))
 files=[{'path':str(p),'bytes':(project/p).stat().st_size,'sha256':sha(project/p)}for p in sorted(set(selected))];write(project/'工程文件清单.json',{'rom_sha256':digest,'files':files});selected.append(Path('工程文件清单.json'))
 source_zip=zipped(project,selected)
 with(stage/'actual_ZIP_rebuild.log').open('w')as stream:subprocess.run([sys.executable,'tools/verify_optimization_archive.py',str(source_zip)],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
 archive_check=read(read('evidence/optimization_20261022/archive_rebuild/latest_attempt.json')['report']);assert archive_check['source_ZIP_sha256']==sha(source_zip)and archive_check['production_ROM_sha256']==digest
 demo=stage/DEMO_NAME;demo.mkdir(exist_ok=True);cp(ROM,demo/ROM_NAME)
 phase=read('evidence/phase_demo_20261021/latest_attempt.json')['report'];gallery=(ROOT/phase).parent
 for p in gallery.glob('*.png'):
  if p.name!='failed.png':cp(p,demo/'实际试玩截图'/p.name)
 room=(ROOT/read('evidence/optimization_20261022/music_room/latest_attempt.json')['report']).parent
 cp(room/'music_room_open.png',demo/'实际试玩截图/音乐欣赏.png')
 sample_pointer=ROOT/'evidence/optimization_20261022/music_room_samples/latest_attempt.json'
 if sample_pointer.exists():
  samples=ROOT/json.loads(sample_pointer.read_text())['report'];sample_report=json.loads(samples.read_text())
  if sample_report['status']=='pass'and sample_report['production_rom_sha256']==digest:
   for item in sample_report['recordings']:cp(samples.parent/item['file'],demo/'音色试听'/item['file'])
   cp(samples,demo/'音色试听/录音说明.json')
 navigation=(ROOT/read('evidence/hardware_scroll/navigation/latest_attempt.json')['report']).parent
 for name in('bottom_left_boundary.png','top_left_boundary.png','pan_up.png'):cp(navigation/name,demo/'实际试玩截图'/name)
 comparison=ROOT/'evidence/optimization_20261022/visual_comparison/result.json'
 if comparison.exists()and json.loads(comparison.read_text())['production_rom_sha256']==digest:
  cp(comparison.parent/'画质对照.png',demo/'画质对照.png')
 perf=read('evidence/performance/frame_rate_20261021.json');now=next(r for r in perf['reports']if r['version']=='development');assert now['rom_sha256']==digest
 walking=next(s for s in now['scenes']if s['scene']=='cave walking up/down');camera=next(s for s in now['scenes']if s['scene']=='cave camera scroll')
 guide=f'''废都物语 GBA · v0.6 画质性能版（2026-10-22）

用 GBA 模拟器打开“{ROM_NAME}”，建议先新游戏，选骑士的嫡子、男性、普通难度。
这是开发 DEMO，供你判断画质、交互与速度是否满意；当前版本可能还有问题。
原剧情、数值、敌人、物品和分支从未改写的原 LCF 读取。全游戏、全部结局和实机尚未验收。

本轮变化
底图、图块、人物原尺寸显示并滚动；取消地图统一压成 15 色的旧方法。
头像保持 48×48；人物颜色能随当前可见人物回收；光标和新画面一起提交以避免闪烁。
地图缓存扩大，来回查看可复用；普通步行不重复遍历整张地图。
剧情换图直接黑屏后显示新图，不使用渐亮渐暗；静态半透明仍保留。
99 首 MIDI 保留原谱与循环，加上 6 首 WAV，共 105 首配乐及 218 个音效。
MIDI 音乐欣赏和游戏过程均为简化音色：欣赏较细的立体声，游戏较粗的单声道。
6 首 WAV 配乐两模式共用已转换录音；试听目录附音乐欣赏页面中的实际录音。
两种音色放在同一个游戏里，没有原音源分册。

操作
方向键行走；L/R 选择调查点，A 沿通路前往调查；L+R 只走过去。
R+方向键只浏览地图。四边三角箭头表示视野还能否继续滚动，不表示地形通行。
黄色地点可达、灰色暂不可达。最初仅入口开放，调查后再开放其它地点。
START 系统菜单；SELECT 原子菜单；A 确认、B 返回。
标题→音乐欣赏：上下选曲，A 播放/暂停，短曲结束后 A 重播；左右或 L/R 换曲播放，START 切换简化音色，B 返回。

抽查结果
本轮 {regression['total']} 项回归通过，含四种出身取名换图、行走/调查、首战、
称号/料理/调和、状态页、存档冷读、地图与完整重建对照、全部头像及密集声音组合。
全部 105 首配乐在两种音色下各播完完整段落；原曲有循环的另覆盖两轮，GBA 定时/队列受控检查通过。
完整乐谱主机检查、独立测试卡的播放检查、自然游戏按键抽查分开记录，不等于完整通关。
同一洞窟短样本：行走约 {walking['engine_updates_per_second']:.1f} 次逻辑更新/秒，
约 {walking['display_updates_per_second']:.1f} 次变化画面/秒；查看地图约 {camera['engine_updates_per_second']:.1f} 次逻辑更新/秒。
静止画面故意不重复重画，这些计数不能称为整场游戏帧率。

仍有差距
GBA 240×160、RGB555 和调色板容量不能完全复刻 PC 原图。
多组头像同屏仍会近似颜色；战斗、部分插图和演出继续小屏适配。
全部后期场景速度、所有支线/结局、完整通关和真机没有计作通过。
工程与详细报告另附，可继续用 AI 修改；并非通用的完整 EasyRPG GBA 版本。

保存
原事件允许时，START→保存游戏。写入普通 v5 SAV，兼容工程旧版 v2/v3/v4/v5。
本包不放同名 SAV。使用旧进度前先复制，再改成新 ROM 对应名称，保留原档。
不读取 PC 存档或模拟器即时存档。原 ROM、旧 DEMO 和用户存档均未覆盖。
'''
 (demo/'试玩说明.txt').write_text(guide,encoding='utf-8-sig')
 for name,report in [('本轮回归.json',regression),('全曲GBA检查.json',{k:v for k,v in music.items()if k!='cases'}),('性能结果.json',{**perf,'reports':[{k:v for k,v in r.items()if k!='commands'}for r in perf['reports']]}),('工程重建校验.json',state['rebuild']),('实际工程ZIP重建校验.json',archive_check)]:write(demo/name,report)
 receipt={'status':'verified_stage_artifacts','rom':ROM_NAME,'rom_sha256':digest,'ROM_bytes':ROM.stat().st_size,'source_archive':source_zip.name,'source_archive_sha256':sha(source_zip),'source_rebuild':'byte-identical; archive/font/site packages disabled','regression_tests':regression['total'],'complete_music_cases':music['total'],'full_game_port':False,'PC_visual_and_performance_parity':'not_established','unverified':['full natural campaign/endings','physical GBA hardware']};write(demo/'交付校验.json',receipt)
 demo_zip=zipped(demo,[p.relative_to(demo)for p in demo.rglob('*')if p.is_file()]);state.update(status='sealed, not delivered',demo=str(demo),source_zip=str(source_zip),demo_zip=str(demo_zip),source_zip_sha256=sha(source_zip),demo_zip_sha256=sha(demo_zip),actual_source_ZIP_rebuild=archive_check);write(STATE,state);print(json.dumps({k:v for k,v in state.items()if k in('status','demo','source_zip','demo_zip')},ensure_ascii=False,indent=2))
def deliver():
 session=read('evidence/optimization_20261022/session.json');now=datetime.datetime.now(datetime.timezone.utc).timestamp();assert now>=session['start_unix']+session['minimum_seconds'],'The requested six real hours have not elapsed'
 digest,receipt,regression=current();state=read(STATE);assert state['status']=='sealed, not delivered'and state['rom_sha256']==digest
 assert state['actual_source_ZIP_rebuild']['status']=='pass'and state['actual_source_ZIP_rebuild']['source_ZIP_sha256']==state['source_zip_sha256']
 for key in('source_zip','demo_zip'):assert sha(Path(state[key]))==state[key+'_sha256']
 assert sha(Path(state['demo'])/ROM_NAME)==digest
 downloads=Path('/mnt/c/Users/APP/Downloads');destinations=[ROOT/'交付',downloads]
 for folder in destinations:
  assert not(folder/DEMO_NAME).exists()
  for key in('source_zip','demo_zip'):assert not(folder/Path(state[key]).name).exists()
 for folder in destinations:
  folder.mkdir(parents=True,exist_ok=True);shutil.copytree(state['demo'],folder/DEMO_NAME)
  for key in('source_zip','demo_zip'):
   shutil.copy2(state[key],folder/Path(state[key]).name);assert sha(folder/Path(state[key]).name)==state[key+'_sha256']
  assert sha(folder/DEMO_NAME/ROM_NAME)==digest
 result={'status':'delivered','delivery_UTC':datetime.datetime.fromtimestamp(now,datetime.timezone.utc).isoformat(),'optimization_wall_seconds':now-session['start_unix'],'rom_sha256':digest,'ROM':str(downloads/DEMO_NAME/ROM_NAME),'DEMO_ZIP':str(downloads/Path(state['demo_zip']).name),'SOURCE_ZIP':str(downloads/Path(state['source_zip']).name),'full_game_port':False,'PC_parity':'not_claimed','hardware':'not_run'};write(ROOT/'evidence/optimization_20261022/delivery.json',result);state['status']='delivered';write(STATE,state);print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','seal','deliver']);args=parser.parse_args();globals()[args.action]()
