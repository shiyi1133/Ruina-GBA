"""Freeze the verified stage demo and verify its matching cached source build."""
import hashlib,json,os,re,shutil,subprocess,sys,zipfile
from pathlib import Path
from project_env import ROOT,arm_prefix

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(path):return json.loads((ROOT/path).read_text())
def copy(source,target):target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
def archive(folder,paths):
 target=folder.parent/(folder.name+'.zip');assert not target.exists()
 with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for relative in sorted(paths):z.write(folder/relative,Path(folder.name)/relative)
 with zipfile.ZipFile(target)as z:assert z.testzip()is None
 return target

def main():
 version=sys.argv[1]if len(sys.argv)>1 else'0.4';assert re.fullmatch(r'\d+(?:\.\d+)+',version)
 suffix={'0.4.1':'透明效果修正','0.4.2':'黑屏切换','0.4.3':'取名后转场修正','0.5':'原尺寸地图硬件滚动','0.5.1':'光标闪烁修正'}.get(version,'地图优化')
 rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=sha(rom)
 attempt=read('evidence/phase_demo_20261021/latest_attempt.json');play=read(attempt['report'])
 assert play['status']=='pass' and play['rom_sha256']==digest
 assert rom.stat().st_size<=33554432
 reports=[attempt['report'],'evidence/performance/map_dirty/result.json','evidence/performance/lcf_cache.json','evidence/full_features/storage_images_host.json','evidence/mechanisms/host_event_integration.json','evidence/audio/result.json','evidence/performance/frame_rate_20261021.json','evidence/performance/drawing/result.json','evidence/mechanisms/functional_status.json']
 if version in ('0.4.3','0.5','0.5.1'):
  naming=read(read('evidence/naming_cut/latest_attempt.json')['report'])
  assert naming['rom_sha256']==digest and naming['status']=='pass' and len(naming['origins'])==4
  reports.append(read('evidence/naming_cut/latest_attempt.json')['report'])
  reports += [v['report']for v in naming['origins']]
 if version in ('0.5','0.5.1'):
  navigation=read('evidence/hardware_scroll/navigation/latest_attempt.json')['report']
  scroll_reports=[navigation,'evidence/hardware_scroll/cache/result.json','evidence/hardware_scroll/native_crop/result.json','evidence/hardware_scroll/objects/result.json']
  for reference in scroll_reports:
   result=read(reference);assert result['status']=='pass'and result.get('production_rom_sha256',result.get('rom_sha256'))==digest
  reports+=scroll_reports
 if version=='0.5.1':
  cursor=read('evidence/cursor_flash/latest_attempt.json')['report'];result=read(cursor)
  assert result['status']=='pass'and result['rom_sha256']==digest
  reports.append(cursor)
  reports.append('evidence/cursor_flash/60a4074b7ad8/continuity.json')
  reports.append('evidence/cursor_flash/release_checks.json')
 for reference in ('evidence/full_features/portraits/latest_attempt.json','evidence/full_features/presentation/latest_attempt.json','evidence/full_features/native_audio/latest_attempt.json'):
  reports.append(read(reference)['report'])
 uniform=ROOT/'evidence/full_features/uniform_alpha/latest_attempt.json'
 if uniform.exists():
  ref=json.loads(uniform.read_text());result=read(ref['report'])
  if result['production_rom_sha256']==digest:assert result['status']=='pass';reports.append(ref['report'])
 assert read('evidence/audio/result.json')['rom_sha256']==digest
 for ref in ('evidence/full_features/portraits/latest_attempt.json','evidence/full_features/presentation/latest_attempt.json'):
  result=read(read(ref)['report']);assert result['status']=='pass' and result['production_rom_sha256']==digest
 native=read(read('evidence/full_features/native_audio/latest_attempt.json')['report'])
 assert native['production_rom_sha256']==digest
 name=f'废都物语_GBA_阶段DEMO_v{version}_20261021';demo=ROOT/'交付'/name
 project=ROOT/'交付'/f'废都物语_GBA_阶段工程_v{version}_20261021'
 assert not demo.exists() and not project.exists(),'Preserve existing stage packages'
 demo.mkdir(parents=True);project.mkdir(parents=True)
 filename=f'废都物语_GBA_DEMO_v{version}_{suffix}.gba';copy(rom,demo/filename)
 if version=='0.5.1':copy(ROOT/'光标闪烁修复说明.txt',demo/'光标闪烁修复说明.txt')
 folder=(ROOT/attempt['report']).parent
 for p in folder.glob('*.png'):
  if p.name!='failed.png':copy(p,demo/'实际试玩截图'/p.name)
 if version in ('0.5','0.5.1'):
  for p in (ROOT/navigation).parent.glob('*.png'):
   if p.name!='failed.png':copy(p,demo/'实际地图操作截图'/p.name)
 portrait=ROOT/read('evidence/full_features/portraits/latest_attempt.json')['report']
 copy(portrait.parent/'dialogue_original_face.png',demo/'验证截图_原始48像素头像.png')
 performance=read('evidence/performance/frame_rate_20261021.json')
 concise={'status':performance['status'],'method':performance['method'],'versions':[{k:v for k,v in r.items()if k!='commands'}for r in performance['reports']],
          'controlled_render_benchmark':{k:v for k,v in read('evidence/performance/drawing/result.json').items()if k!='rows'},
          'controlled_facing_changes':[{k:v for k,v in r.items()if k!='commands'}for r in read('evidence/performance/drawing/result.json')['rows']],
          'native_MIDI_pressure_test':{'status':native['status'],'seconds':native['seconds'],'source_position_ratio':native['source_position_ratio']},
          'static_scene_redraw_count_is_not_FPS':True,'physical_hardware':'not_run'}
 if version in ('0.5','0.5.1'):
  concise.pop('controlled_facing_changes');concise['controlled_render_benchmark']={k:v for k,v in read('evidence/hardware_scroll/cache/result.json').items()if k!='records'}
 (demo/'性能结果.json').write_text(json.dumps(concise,ensure_ascii=False,indent=2))
 for path in reports:copy(ROOT/path,demo/'验证记录'/path)
 guide='''废都物语 GBA · 阶段 DEMO v0.4（2026-10-21）

这个版本供你判断：目前的画面、交互和速度，是否值得继续做下去。
本轮阶段任务已完成，但全游戏移植尚未完成，当前版本可能还有问题。

打开“废都物语_GBA_DEMO_v0.4_地图优化.gba”，建议先选新游戏。
推荐先选“骑士的嫡子”、男性、普通难度，体验地图移动、调查入口及第一场战斗。
本包不预放同名 SAV，不覆盖之前的 DEMO 或你的存档。

本轮变化
- 地图只更新发生变化的区域，并提前跳过区域外地砖和人物。
- 图片只展开用到的像素列，固定 ROM 资料重复查询使用小缓存。
- 地图光标改为硬件精灵；地图人物仍使用局部位图绘制。
- 对话头像保留原始 48×48 像素和原图颜色（GBA RGB555 精度）。
- 场景转场直接黑屏，图片准备好后直接显示，去掉渐亮渐暗和额外转场等待。
- 补齐取名后的图片透明度渐变与屏幕色调渐变，两者也直接切换到目标状态。
- 静态半透明效果继续保留；图片位置、缩放和地图卷动继续保留交互所需的运动。
- 音频混合减少空通道检查，游戏规则和原始剧情数据不因此改写。
- 半透明图片使用均匀颜色混合，已取消大面积斜纹网点。

实际按键抽查通过
新游戏与取名、实际行走、调查入口、调查点切换、系统菜单进出、第一场战斗胜利，
以及新普通存档保存后冷启动、旧 DEMO 普通存档冷启动。
局部绘制另有 12 组与完整重画逐像素对照；头像、均匀半透明与黑屏切换另有独立显示测试。
取名结束到进入洞窟，四种出身分别以真实按键逐硬件帧观察；未出现中间亮度或透明度。
已观察到准备新图时的实际纯黑画面；旧版 v0.4.2 的失败复现记录保留在开发目录。
这些是开发抽查，未声称完整通关或 GBA 实机通过。

如实说明速度与问题
地图已有改善，仍会停顿，尚未达到流畅完成版水平。
洞窟的短时实际行走样本约 1.6 次画面更新/秒、12.9 次逻辑更新/秒。
“画面更新”是有变化才呈现，不是持续刷新帧率；静止地图不重复绘制。
持续转向的受控绘制样本约 4.8 次更新/秒，也不能当作整场游戏 FPS。
PCM 配乐输出通过抽查；实时 MIDI 的 battle10 单曲压力测试仍失败，
约为正常播放进度的 94.7%，可能出现卡音和掉速。没有把这个问题计作通过。
后期剧情、全部支线/结局、全部音乐及实机表现仍未完成验收。
地图仍有 GBA 所需的缩放和减色。开场大片空白与逐步揭示的探索地图属于原游戏设计。
本版半透明颜色按 GBA 调色板近似，精度有限，但不再使用斜纹网点。

操作
方向键行走；A 调查、确认；B 返回；START 打开菜单。
L/R 切换调查点，A 沿通行路线走过去调查；L+R 只走过去。
开场最初只有入口一个调查点，调查后才开放其它地点。
START → 保存游戏，在原事件允许保存时写入普通 SAV。
模拟器键位以你自己的设置为准。

建议观察：移动时的停顿、调查点光标响应、中文和头像可读性、战斗操作和声音。
无需为开发者完整通关；若你愿意继续体验后续流程，请保留遇到问题时的普通 SAV。
“验证截图_原始48像素头像.png”来自独立显示测试，其余截图来自本 ROM 的真实操作。
匹配工程另存于“废都物语_GBA_阶段工程_v0.4_20261021.zip”，可独立增量重建本 ROM。
'''
 live=next(v for v in performance['reports']if v['version']=='development');walking=next(s for s in live['scenes']if s['scene']=='cave walking up/down')
 assert live['rom_sha256']==digest,'Performance observations must match this ROM'
 rendering=read('evidence/performance/drawing/result.json')['rows'][-1]
 guide=re.sub(r'v0\.4(?![\d.])',f'v{version}',guide).replace('_地图优化.gba',f'_{suffix}.gba')
 guide=guide.replace('1.6 次画面更新',f"{walking['display_updates_per_second']:.1f} 次画面更新").replace('12.9 次逻辑更新',f"{walking['engine_updates_per_second']:.1f} 次逻辑更新").replace('4.8 次更新',f"{rendering['map_updates_per_second']:.1f} 次更新").replace('94.7%',f"{native['source_position_ratio']*100:.1f}%")
 if version in ('0.5','0.5.1'):
  scrolling=next(s for s in live['scenes']if s['scene']=='cave camera scroll')
  guide=f'''废都物语 GBA · 阶段 DEMO v{version}（2026-10-21）

打开“{filename}”，建议先选新游戏，关闭开场说明框后查看入口标记。
这是供你判断效果和继续投入价值的开发 DEMO，当前版本可能还有问题。
全游戏移植、全部音乐和全部剧情仍未完成验收。

本轮变化
探索地图按原尺寸显示，60 张底图、8 套图块、9 套人物图集不再缩小。
背景改用图块缓存和硬件滚动：只补入新边缘，已缓存的区域不重复重画。
人物、地点、当前位置、小型 HUD、四边三角箭头使用硬件精灵。
黄标可调查，灰标暂不可达，蓝标是当前位置；选中地点显示“调查／受阻”。
四边箭头可继续滚动时高亮，到地图边缘变灰。
原有调色板减色仍在；对话、战斗、画廊和制作界面继续使用小屏适配。
切屏仍是直接黑屏后显示新图，不恢复渐亮渐暗。

操作
方向键移动当前位置；短按 L/R 选择调查点，A 前往调查。
按住 R+方向键只查看地图，不移动角色；三角箭头表示视野边界，不代表地形通行。
START 打开菜单；SELECT 保留原作子菜单。
开场未探索区域仍会被原游戏遮挡，不提前显示未开放的秘密地点。

已完成开发抽查
模拟器真实按键：开场四种出身取名、入口默认显示、四向查看地图、箭头明暗、
标记闪烁、调查入口、地图移动、菜单进出、第一场战斗、普通存档保存和新旧存档冷启动。
缓存与完整重建有 15 组逐像素对照；另有原尺寸底图裁剪、九套角色和 HUD 调色板、
从地图进入原始 48×48 对话头像后再返回地图的显示抽查。
横移一格只补入 40 个背景图块，纵移一格补入 60 个；转向和标记闪烁不上传背景。
这些抽查不等于完整通关或实机测试通过。

速度与已知问题
洞窟短样本：实际移动约 {walking['display_updates_per_second']:.1f} 次显示更新/秒，
约 {walking['engine_updates_per_second']:.1f} 次逻辑更新/秒；查看地图约 {scrolling['display_updates_per_second']:.1f} 次显示更新/秒。
这是有变化才呈现的计数，不是整场游戏持续 FPS；背景上传、OBJ 更新和逻辑分别记录。
仍有停顿，尚未成为流畅完成版。PCM 配乐抽查通过，实时 MIDI 压力测试仍失败，
battle10 约为正常进度的 {native['source_position_ratio']*100:.1f}%，可能有卡音和掉速。
后期剧情、所有支线/结局、全部音乐及 GBA 实机表现仍未完成验收。

未覆盖先前 DEMO、原游戏和你的 SAV。本包不预放同名存档。
匹配工程：废都物语_GBA_阶段工程_v{version}_20261021.zip，可独立增量重建同一 ROM。
详细说明见对应工程的“原尺寸地图说明.txt”。
'''
 if version=='0.5.1':
  guide=guide.replace('本轮变化\n','本轮修正\n移动光标时保留当前人物与标记，等下一画面准备好后在屏幕刷新间隙一起显示。\n较远地点采用分段硬件滚动，不因选点或行走而临时黑屏。\n角色图像按内容复用，普通行走不再重复搜索整张地图的通路。\n每帧连续观察 1650 帧，光标、行走和浏览没有出现整屏黑帧或箭头消失；\n旧版相同步骤检测到 37 帧箭头短暂消失，失败记录随包保留。\n\n已保留的地图功能\n')
  guide=guide.replace('切屏仍是直接黑屏后显示新图，不恢复渐亮渐暗。','剧情换图仍是直接黑屏后显示新图；地图内移动光标持续保留画面。')
 assert filename in guide and f'阶段 DEMO v{version}（'in guide
 (demo/'试玩说明.txt').write_text(guide,encoding='utf-8-sig')
 selected=[]
 for directory in ('source','runtime','platform','tools','tests','third_party','research/reference'):
  selected += [p.relative_to(ROOT)for p in (ROOT/directory).rglob('*')if p.is_file()and '__pycache__'not in p.parts]
 selected += [p.relative_to(ROOT)for p in ROOT.glob('*.txt')]
 for name0 in ('build/assets.c','build/assets.h','build/asset_manifest.json','build/original_lcf.bin','build/audio.bin','build/audio_manifest.json','build/portraits.bin','build/portraits_manifest.json','build/palette_lookup.bin','build/palette_lookup_manifest.json','build/native_music/native_soundfont.bin','build/native_music/manifest.json','build/build_receipt.json'):
  selected.append(Path(name0))
 selected += [p.relative_to(ROOT)for p in (ROOT/'build/original').glob('*')if p.is_file()]
 selected += [p.relative_to(ROOT)for p in (ROOT/'build/audio_cache').glob('*.mid')]
 selected += [Path(p)for p in reports]
 selected += [Path('evidence/save_cold_load/ordinary.sav')]
 selected=list(dict.fromkeys(selected))
 for relative in selected:copy(ROOT/relative,project/relative)
 instructions='''本阶段匹配工程 v0.4

保留 build/ 中已转换的构建输入，不含用户原始 ZIP、字体安装文件或工具链。
Linux / WSL 安装 Python 3 和 GNU Arm Embedded 工具链后执行：
  python3 tools/build.py --incremental
可通过 ARM_TOOLCHAIN_PREFIX 指定 arm-none-eabi- 工具前缀。
增量重建不需要原始游戏 ZIP；重新转换素材需要你自己的原 ZIP 与中文字体。
文件清单和哈希见 source_manifest_stage.json，ROM 哈希见阶段重建校验.json。

参考与选择性适配来源、许可证保留于 third_party/；TinySoundFont 许可在 research/reference/tsf.h。
测试用原始普通 SAV 放在 evidence/，不会自动成为同名游戏存档。
部分历史对比测试依赖旧版 history/ ROM，本阶段包没有重复附带历史 ROM。
验证记录区分通过、失败和未运行；实时 MIDI 性能尚未通过，完整游戏没有通关验收。
'''
 (project/'本阶段工程重建说明.txt').write_text(instructions.replace('v0.4',f'v{version}'),encoding='utf-8-sig');selected.append(Path('本阶段工程重建说明.txt'))
 env=os.environ.copy();env['ARM_TOOLCHAIN_PREFIX']=arm_prefix();env['RUINA_SOURCE_ARCHIVE']='/nonexistent_stage_rebuild_archive.zip'
 with (project/'stage_rebuild.log').open('w')as output:
  subprocess.run([sys.executable,'tools/build.py','--incremental'],cwd=project,env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
 rebuilt=project/'build/废都物语_GBA_开篇开发验证版.gba';assert sha(rebuilt)==digest,'Source rebuild differs from verified demo'
 check={'status':'pass','expected_rom_sha256':digest,'rebuilt_rom_sha256':sha(rebuilt),'original_archive_access':'disabled by nonexistent path','cached_incremental_build':True,'not_native_Windows_build':True}
 (project/'阶段重建校验.json').write_text(json.dumps(check,ensure_ascii=False,indent=2));selected += [Path('阶段重建校验.json'),Path('stage_rebuild.log')]
 manifest={'rom_sha256':digest,'files':[{'path':str(p),'sha256':sha(project/p)}for p in sorted(selected)]}
 (project/'source_manifest_stage.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));selected.append(Path('source_manifest_stage.json'))
 source_zip=archive(project,selected)
 receipt={'name':name,'rom':filename,'bytes':rom.stat().st_size,'sha256':digest,'full_game_port':False,'spot_check':play['checks'],'native_MIDI_pressure_test':native['status'],'native_MIDI_source_position_ratio':native['source_position_ratio'],'source_archive':source_zip.name,'source_rebuild':'byte-identical, original ZIP disabled','unverified':['full campaign and endings','all music playback','physical GBA hardware']}
 (demo/'交付校验.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 demo_zip=archive(demo,[p.relative_to(demo)for p in demo.rglob('*')if p.is_file()])
 downloads=Path('/mnt/c/Users/APP/Downloads');assert not (downloads/name).exists()
 shutil.copytree(demo,downloads/name)
 for p in (demo_zip,source_zip):assert not (downloads/p.name).exists();shutil.copy2(p,downloads/p.name)
 assert sha(downloads/name/filename)==digest
 result={'status':'delivered','demo_zip':str(downloads/demo_zip.name),'rom':str(downloads/name/filename),'source_zip':str(downloads/source_zip.name),'sha256':digest,'source_rebuild':'pass byte-identical','full_game_port':False}
 (ROOT/'evidence/phase_demo_20261021/delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
