"""Stage, verify, seal and deliver v0.7 without replacing old releases/saves.

The current six-real-hour request gates delivery, not preparation. Evidence
and the matching source ZIP must pass before any final artifact is copied.
"""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,time
from pathlib import Path
from project_env import ROOT,arm_prefix
from deliver_optimization import inputs,cp,zipped
from collect_balanced_acceptance import collect
from verify_balanced_archive import verify

BASE=ROOT/'evidence/balanced_optimization_20261023'
STATE=BASE/'release_preparation.json'
SOURCE_NAME='废都物语_GBA_匹配工程_v0.7_20261023'
DEMO_NAME='废都物语_GBA_v0.7_均衡画质可玩版_20261023'
ROM_NAME='废都物语_GBA_v0.7_均衡画质可玩版.gba'
ROM=ROOT/'build/废都物语_GBA_开篇开发验证版.gba'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,value):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def current():
    receipt=read(ROOT/'build/build_receipt.json');assert receipt['sha256']==sha(ROM)and receipt['version']=='0.7'and ROM.stat().st_size<=33554432
    assert all(sha(ROOT/p)==h for p,h in receipt['compiler_inputs_sha256'].items())
    return receipt
def selected_inputs():return sorted(set(inputs()+[Path('history/balanced_optimization_20261023/baseline/build/build_receipt.json')]))

def performance_note(acceptance):
    digest=acceptance['ROM_sha256'];shop=read(BASE/'shop_comparison'/digest[:12]/'result.json')
    assert shop['production_ROM_sha256']==digest
    rows=acceptance['response']+acceptance['battle_response']+acceptance['battle_menu_response']+shop['current_response']
    groups=[('标题选项',['title_menu_down','title_menu_up']),('头像选项',['avatar_down','avatar_up']),('取名光标',['name_cursor_right','name_cursor_left']),('首次地图步行',['map_walk_up','map_walk_down']),('打开地图菜单',['map_open_menu']),('地图菜单选项',['map_menu_down','map_menu_up']),('关闭地图菜单',['map_close_menu']),('浏览地图',['map_camera_up','map_camera_down']),('第一战选项',['battle_mode_menu_down','battle_mode_menu_up','battle_actor_menu_down','battle_actor_menu_up']),('战斗技能与物品光标',['skill_list_down','skill_list_up','item_list_down','item_list_up']),('战斗进入子菜单',['enter_skill_list','enter_item_list','choose_item_target']),('战斗返回上级',['cancel_target_to_items','cancel_items_to_actor','cancel_skills_to_actor','cancel_actor_to_battle_root']),('商店物品列表',['shop_sell_down','shop_sell_up']),('买卖数量变化',['quantity_plus1','quantity_minus1','quantity_plus10','quantity_minus10'])]
    text=['v0.7 性能与画质说明','ROM SHA-256：'+digest,'','以下按真实 GBA 模拟周期计时，记录按下按键到完整新画面出现的时间。','不使用电脑运行模拟器的倍速作为游戏性能。静止画面不重画，也不算作零帧。','场景为开场、首次洞窟、第一战、原第一 CP 首领战菜单及受控商店；没有据此推断全部后期地图的速度。','','操作 / 观察范围（毫秒） / 样本数']
    for name,keys in groups:
        selected=[r for r in rows if r['action']in keys];assert len(selected)==len(keys)
        low=min(r['response_ms_min']for r in selected);high=max(r['response_ms_max']for r in selected)
        text.append(f'{name}：{low:.1f}–{high:.1f} ms，{sum(r["samples"]for r in selected)} 个样本')
    observed=sum(r['samples']for r in rows);black=sum(r['black_frames']for r in rows)
    text += ['',f'这些检查还包含取名切换等操作，共 {observed} 个按键样本，观察到的整屏黑帧合计 {black}。','首次自然地图完整绘制约 0.57 秒；这与之后的光标、滚动和菜单响应分开统计。','取名切换整套姓氏/名字用字约 84–100 ms，大型物品列表翻页也可能更慢。','比较原完整刷新实现，商店列表约 117–268 ms → 50–100 ms；数量窗口约 100–134 ms → 33–67 ms。','商店两版的像素、物品顺序、价格、库存和交易后完整 Game 状态一致。','战斗菜单取消时保留上级光标，不扣除资源；48 个状态与完整重绘逐像素一致。','复用未变化的背景，并在未显示的显存区域暂存一小块 RGB555 背景；不降低敌人画质。','','画质取舍','探索地图与人物按原尺寸显示并滚动，不把整张地图统一缩小。','原始头像各自保留 RGB555 颜色；插图与战斗使用 GBA 240×160 的适配布局。','地图仍受最多 240 个背景颜色和人物调色板容量限制，超出容量时会近似颜色。','RGB555 仍低于 PC 原图的颜色精度，部分原动画已按要求简化。','多组头像对照图是受控测试，不能当作自然剧情截图；普通开场画面另附。','所有展示图来自实际 GBA 模拟器输出，仅使用整数倍放大，无增强或 AI 重绘。','','验证范围','36 项通用回归、四种出身开场、首战、料理/调和/称号及普通存档冷读。','41 个 RGB 图像案例、54 个菜单状态，以及 61 张地图共 610 个窗口/恢复状态。','105 首配乐×两种简化音色共 210 项整曲检查；音乐欣赏另测 128 次循环。','完整自然通关、全部结局、真正 GBA 硬件及所有场景达到 PC 画面/性能水平仍未验收。','详细数据见同目录“本轮验证.json”；完整报告和历史失败记录保留在匹配工程中。']
    return '\n'.join(text)+'\n'

SOURCE_GUIDE='''匹配工程 v0.7（2026-10-23）

Linux/WSL 安装 Python 3 与 GNU Arm Embedded 工具链后，在本目录运行：
  python3 tools/build.py --incremental
ARM_TOOLCHAIN_PREFIX 可指定 arm-none-eabi- 前缀。
build/ 包含已转换的完整游戏资源。重建无需原 ZIP、字体或 Python 图像库。
本包从实际 ZIP 新解压，以 python3 -S 重建并与试玩 ROM 逐字节核对。
不附工具链或编译程序；Windows 原生构建未测。

显示优化入口：platform/gba/video.c、rgb_surface.inc、native_ui.inc、image.c。
共用规则在 runtime/rm2k/；本作启动、自制列表和音乐欣赏在 source/。
同屏头像保留独立 RGB555 颜色，地图保留原尺寸；菜单与地图分层。
剧情、物品、配方和敌人数值来自原 LCF，不在本轮重写。

需要重新转换素材时，设置 RUINA_SOURCE_ARCHIVE、RUINA_FONT，并使用带 Pillow/NumPy 的 Python。
重建简化音乐：python3 tools/rebuild_simplified_audio.py（需要 NumPy）。
代码许可、上游版本和素材来源见 CREDITS.txt、LICENSE、third_party/。
代码开源不改变原游戏素材的权利归属；本工程并非完整 EasyRPG 的 GBA 移植。

验证需 mGBA 开发库，设置 MGBA_PREFIX 后执行 python3 tools/build_probe.py。
通用回归：python3 tools/validate_optimization.py（设置 RUINA_ASSET_PYTHON 指向带图像库的 Python）。
当前整套验证入口：python3 tools/validate_balanced.py；--skip-music 仅做部分检查，不生成最终通过。
显示专测：check_balanced_rgb、check_balanced_menu_regions、check_balanced_ui_capacity。
自然开场：check_balanced_playable --origin 1（另测 2、3、4）。
列表效果对照：check_incremental_rooms；实际音乐欣赏：check_music_room_long。
全部原生地图的窗口/头像/存档/插图返回：check_map_window_matrix（游戏音色）。
存档编码与声音补充回调的逐字节检查：check_serviced_storage。
物品列表原编号顺序：check_shop_item_order；原商店显示/交易对照：check_shop_comparison。
物品栏筛选、翻页、说明、返回编号及原像素对照：check_inventory_matrix。
全曲测试：check_music_full_scores_parallel（独立模拟器并行完整检查，默认 4 个）；check_music_full_scores_gba 保留串行入口。
战斗层级与像素对照：check_battle_menu_comparison；取消资源与连续按键：check_battle_menu_navigation。
全部均为 tools/ 下同名 .py 文件。
tools/collect_balanced_acceptance.py 只汇总同一 ROM 哈希的完整报告，缺项会失败。
最终汇总：evidence/balanced_optimization_20261023/final_acceptance.json。
报告保留历史失败和未运行状态，不把旧 ROM 的结果当作当前版本通过。
源码包保留报告和日志，实际截图与画面对照放在试玩包；不附全部历史截图、测试卡和录音。

交付入口为 tools/deliver_balanced.py。旧 deliver_* 与 package_* 脚本属于历史版本。
历史测试/性能对比可能另需旧 ROM、旧即时产物或用户原 ZIP；这些不包含在源码包中。
正常重建、当前回归及新显示层测试不依赖 experiments/ 中的临时实验源码。
完整自然通关、全部结局和真正 GBA 硬件仍未验收。
'''

def prepare():
    receipt=current();digest=receipt['sha256'];stage=Path(tempfile.mkdtemp(prefix='ruina-v07-release-',dir='/tmp'));project=stage/SOURCE_NAME;project.mkdir()
    selected=selected_inputs();snapshot={str(p):sha(ROOT/p)for p in selected}
    for p in selected:cp(ROOT/p,project/p)
    (project/'工程使用说明.txt').write_text(SOURCE_GUIDE,encoding='utf-8-sig')
    env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_v07_original.zip',RUINA_FONT='/nonexistent_v07_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_v07_asset_python')
    started=time.monotonic()
    with(project/'工程重建日志.txt').open('w')as stream:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    assert sha(project/'build/废都物语_GBA_开篇开发验证版.gba')==digest
    assert all(sha(ROOT/p)==h and sha(project/p)==h for p,h in snapshot.items())
    rebuild={'status':'pass','production_ROM_sha256':digest,'rebuilt_ROM_sha256':digest,'byte_identical':True,'original_archive_font_asset_python':'disabled by nonexistent paths','Python_site_packages':'disabled by -S','host_seconds':time.monotonic()-started,'environment':'Linux/WSL with external GNU Arm; native Windows not tested'}
    write(project/'工程重建校验.json',rebuild)
    state={'status':'prepared, not delivered','rom_sha256':digest,'stage':str(stage),'project':str(project),'selected_source':list(snapshot),'prepared_source_sha256':snapshot,'rebuild':rebuild};write(STATE,state)
    print(json.dumps({k:state[k]for k in('status','rom_sha256','project')},ensure_ascii=False,indent=2))

def seal():
    receipt=current();acceptance=collect();digest=receipt['sha256'];state=read(STATE);assert state['status']=='prepared, not delivered'and state['rom_sha256']==digest
    assert {str(p)for p in selected_inputs()}==set(state['prepared_source_sha256']),'Inputs were added/removed; prepare again'
    assert all(sha(ROOT/p)==h for p,h in state['prepared_source_sha256'].items()),'An input changed; prepare again'
    stage=Path(state['stage']);project=Path(state['project']);selected=[Path(p)for p in state['selected_source']]
    for p in(ROOT/'evidence').rglob('*'):
        if p.is_file()and p.suffix in('.json','.log','.txt')and p!=STATE and'release_preparation'in p.name:continue
        if p.is_file()and p.suffix in('.json','.log','.txt')and p!=STATE:
            rel=p.relative_to(ROOT);cp(p,project/rel);selected.append(rel)
    selected += [Path(p)for p in('工程使用说明.txt','工程重建日志.txt','工程重建校验.json')]
    manifest=[{'path':str(p),'bytes':(project/p).stat().st_size,'sha256':sha(project/p)}for p in sorted(set(selected))]
    write(project/'工程文件清单.json',{'rom_sha256':digest,'files':manifest});selected.append(Path('工程文件清单.json'))
    source_zip=zipped(project,selected);archive=verify(source_zip);assert archive['production_ROM_sha256']==digest
    demo=stage/DEMO_NAME;demo.mkdir();cp(ROM,demo/ROM_NAME)
    opening=BASE/digest[:12]/'opening_1';phase=ROOT/'evidence/phase_demo_20261021'/digest[:12]
    gallery={opening/'title.png':'标题.png',opening/'dialogue_000.png':'开场插图.png',opening/'four_faces.png':'四组头像.png',opening/'name.png':'简易取名.png',opening/'first_map.png':'首次地图.png',phase/'first_battle.png':'第一战.png',BASE/digest[:12]/'battle_response/actor_menu.png':'战斗选项.png',phase/'first_victory.png':'首战胜利.png',phase/'after_cold_load.png':'普通存档恢复.png',BASE/'music_room_long'/digest[:12]/'after_two_loops.png':'音乐欣赏.png'}
    gallery[BASE/digest[:12]/'attribution/credits.png']='制作信息.png'
    for source,name in gallery.items():cp(source,demo/'实际截图'/name)
    visual=BASE/'visual_comparison';comparison=read(visual/'result.json');assert comparison['production_ROM_sha256']==digest
    assert all(sha(visual/name)==value for name,value in comparison['sheets'].items())
    mixed=read(visual/'mixed_portraits/result.json');assert mixed['production_ROM_sha256']==digest and not mixed['new_original_color_mismatches']and sha(visual/mixed['comparison'])==mixed['comparison_sha256']
    for p in visual.glob('*.png'):cp(p,demo/p.name)
    guide=f'''废都物语 GBA · v0.7 均衡画质可玩版

打开“{ROM_NAME}”即可开始。包含完整原游戏数据，可继续游玩并使用普通 SAV。
本轮优化已合入正常游戏；画面预览中的只读看图限制不用于此版。
原剧情、数值、配方、敌人和奖励未改写。完整流程由玩家继续验收，当前仍可能存在未发现的问题。

画面：地图/人物保持原尺寸并滚动，菜单另用显示层；普通选项移动不黑屏。
头像各自保留原 RGB555 色彩。插图适配 240×160；少量地图颜色仍受调色板容量限制。
场景换图先黑屏，准备好后直接显示，不使用淡入淡出。静态半透明保留。
声音：105 首配乐（99 MIDI、6 WAV）和 218 个音效；游戏与音乐欣赏均为简化音色。
音乐欣赏音色稍细，游戏内进一步简化，不提供原音源分册。

地图操作
方向键移动，取消之前选中的远处调查目标；A 调查脚下或面前。
L/R 选择调查点，A 沿通路走过去调查；L+R 只走过去。
R+方向键浏览地图。四边三角箭头表示视野边界，不表示地形是否能走。
黄标可达，灰标暂不可达；开场先调查唯一开放的入口，再开放其它地点。
START 系统菜单，SELECT 原子菜单，A 确认，B 返回。
取名提供常见姓和名字用字；L/R 切换，B 删除，SELECT 恢复原名，START 完成。

标题→音乐欣赏：上下选择，A 播放/暂停，左右或 L/R 换曲播放，START 换简化音色，B 返回。
进游戏后恢复较省性能的音色。

保存
原事件允许保存时，START→保存游戏，使用 v5 普通 SRAM 存档，读取工程 v2/v3/v4/v5。
本包不带同名 SAV。先复制旧存档，再改为新 ROM 对应名称；保留原档。
不读取 PC 原版存档或模拟器即时存档。

本版验证
36 项通用回归、四种出身开场、首战、菜单/配方/称号、普通存档冷读已抽查。
41 个 RGB 图像案例、54 个菜单状态、超量文字后备、237 个底图裁剪及全部头像组合另行受控测试。
另覆盖 61 张原生地图的窗口、头像、滚动、保存及插图返回，610 个状态与完整重建对照。
物品栏另有 68 个状态对照，商店验证了数量变化、售罄、金钱增加与完整状态一致。
105 首配乐在两种音色下共 210 项整曲检查；有循环的覆盖初次播放加一次完整重复。
性能结果、截图与原图差异报告随包提供；测量依据 GBA 模拟周期，不是电脑模拟器倍速。
完整自然通关、全部结局、所有后期场景速度和真正 GBA 硬件尚未验收。
本轮最终交付不代表已完全复刻 PC 画面/性能，也不是完整 EasyRPG 的 GBA 移植。

匹配源码另有 ZIP，含转换资源和重建说明；可继续用 AI 修改。来源/许可证保留在工程中。
'''
    (demo/'试玩说明.txt').write_text(guide,encoding='utf-8-sig')
    (demo/'性能与画质说明.txt').write_text(performance_note(acceptance),encoding='utf-8-sig')
    write(demo/'本轮验证.json',acceptance);write(demo/'实际工程ZIP重建校验.json',archive);write(demo/'原像素核对.json',mixed);write(demo/'原作数据校验.json',read(BASE/'content_identity.json'))
    write(demo/'交付校验.json',{'ROM':ROM_NAME,'ROM_sha256':digest,'ROM_bytes':ROM.stat().st_size,'source_ZIP':source_zip.name,'source_ZIP_sha256':sha(source_zip),'archive_rebuild':'byte identical','full_campaign':'not_run; user acceptance','physical_hardware':'not_run'})
    demo_zip=zipped(demo,[p.relative_to(demo)for p in demo.rglob('*')if p.is_file()])
    from check_balanced_distribution import verify_demo
    distribution=verify_demo(demo_zip,digest);assert distribution['status']=='pass'
    state.update(status='sealed, not delivered',demo=str(demo),source_zip=str(source_zip),demo_zip=str(demo_zip),source_zip_sha256=sha(source_zip),demo_zip_sha256=sha(demo_zip),archive_rebuild=archive,distribution_smoke=distribution);write(STATE,state)
    print(json.dumps({k:state[k]for k in('status','demo','source_zip','demo_zip')},ensure_ascii=False,indent=2))

def deliver():
    session=read(BASE/'session.json');now=time.time();assert now>=session['start_unix']+session['minimum_seconds'],'The current six-real-hour optimization window has not elapsed'
    recovery=read(BASE/'recovery_session.json');assert now>=recovery['supplementary_not_before_unix'],'Do not count the offline outage toward active optimization time'
    receipt=current();acceptance=collect();state=read(STATE);assert state['status']=='sealed, not delivered'and receipt['sha256']==state['rom_sha256']
    assert {str(p)for p in selected_inputs()}==set(state['prepared_source_sha256'])
    assert all(sha(ROOT/p)==h for p,h in state['prepared_source_sha256'].items())
    for key in('source_zip','demo_zip'):assert sha(Path(state[key]))==state[key+'_sha256']
    assert sha(Path(state['demo'])/ROM_NAME)==state['rom_sha256']and state['archive_rebuild']['byte_identical']
    destinations=[]
    for parent in(ROOT/'交付',Path('/mnt/c/Users/APP/Downloads')):
        parent.mkdir(exist_ok=True)
        for source in [Path(state['source_zip']),Path(state['demo_zip']),Path(state['demo'])]:assert not(parent/source.name).exists(),('Will not overwrite release',parent/source.name)
    for parent in(ROOT/'交付',Path('/mnt/c/Users/APP/Downloads')):
        for key in('source_zip','demo_zip'):
            source=Path(state[key]);target=parent/source.name;shutil.copy2(source,target);assert sha(target)==sha(source);destinations.append(str(target))
        target=parent/Path(state['demo']).name;shutil.copytree(state['demo'],target)
        assert all(sha(target/p.relative_to(state['demo']))==sha(p)for p in Path(state['demo']).rglob('*')if p.is_file());destinations.append(str(target))
    record={'status':'delivered','ROM_sha256':receipt['sha256'],'elapsed_wall_seconds_including_offline_gap':now-session['start_unix'],'active_optimization_seconds_excluding_offline_gap':recovery['previous_goal_accounted_seconds']+now-recovery['unix'],'minimum_required_seconds':session['minimum_seconds'],'session_start_unix':session['start_unix'],'delivered_unix':now,'source_ZIP_sha256':state['source_zip_sha256'],'demo_ZIP_sha256':state['demo_zip_sha256'],'destinations':destinations,'originals_and_saves':'preserved','unverified':acceptance['unverified']};write(BASE/'delivery_receipt.json',record)
    state['status']='delivered';write(STATE,state);print(json.dumps(record,ensure_ascii=False,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','seal','deliver']);args=p.parse_args();globals()[args.action]()
