"""Package the scoped RGB555 opening preview and verify its actual source ZIP.

The playable v0.6.2 ROM and all previous deliveries remain immutable.
"""
import datetime,hashlib,json,os,shutil,subprocess,sys,time,zipfile
from pathlib import Path
from project_env import ROOT,arm_prefix

DATE='20261022'
BASE_SHA='1db4e8b86af4cc3b4e71abdc983f9a8e5a2c84eb5784738258912a75750e1561'
BASE_ZIP=Path('/mnt/c/Users/APP/Downloads/废都物语_GBA_匹配工程_v0.6.2_20261022.zip')
BASE_ZIP_SHA='e7c9dc866b95162046d8e235a3449687217fd56cf88c9903972fcf842b67c7a1'
DEMO_NAME='废都物语_GBA_开场画质预览_局部刷新修正版_'+DATE
SOURCE_NAME='废都物语_GBA_开场画质预览_局部刷新匹配工程_'+DATE
ROM_NAME='废都物语_GBA_开场画质预览_RGB555_局部刷新修正版.gba'
SKIP_SUFFIX={'.gba','.elf','.o','.so','.exe','.pyc','.su'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text())
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def cp(src,dst):
    dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def allowed(p):return p.suffix.lower() not in SKIP_SUFFIX and '__pycache__' not in p.parts and p.name!='gba_acceptance_probe'


def extract(archive,parent,target_name=None):
    with zipfile.ZipFile(archive)as z:
        assert z.testzip()is None
        names=z.namelist();assert len(names)==len(set(names))
        roots={Path(n).parts[0]for n in names};assert len(roots)==1
        for n in names:assert not Path(n).is_absolute()and '..'not in Path(n).parts
        z.extractall(parent)
    project=parent/next(iter(roots))
    if target_name and project.name!=target_name:
        target=parent/target_name;assert not target.exists();project.rename(target);project=target
    return project


def rebuild(project,log,expected):
    env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_quality_original.zip',RUINA_FONT='/nonexistent_quality_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_quality_asset_python')
    started=time.monotonic()
    with log.open('w')as out:
        for command in ([sys.executable,'-S','tools/build.py','--incremental'],[sys.executable,'-S','tools/build_quality_preview.py']):
            subprocess.run(command,cwd=project,env=env,stdout=out,stderr=subprocess.STDOUT,check=True)
    base=project/'build/废都物语_GBA_开篇开发验证版.gba';preview=project/'build/fixtures/quality_preview/quality_preview.gba'
    assert sha(base)==BASE_SHA and sha(preview)==expected
    return {'status':'pass','base_v062_ROM_sha256':sha(base),'quality_preview_ROM_sha256':sha(preview),'original_archive_access':'disabled by nonexistent path','font_access':'disabled by nonexistent path','asset_python_access':'disabled by nonexistent path','python_site_packages':'disabled by -S','environment':'Linux/WSL, external GNU Arm toolchain; native Windows not tested','wall_seconds':time.monotonic()-started}


def zip_folder(folder,paths):
    target=folder.parent/(folder.name+'.zip');assert not target.exists()
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
        for p in sorted(paths):z.write(folder/p,Path(folder.name)/p)
    with zipfile.ZipFile(target)as z:assert z.testzip()is None
    return target


def main():
    build=read(ROOT/'evidence/quality_preview/build.json');digest=build['ROM_sha256'];rom=Path(build['ROM']);assert sha(rom)==digest and rom.stat().st_size<=33554432
    assert build['base_v062_ROM_sha256']==BASE_SHA and sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba')==BASE_SHA
    for p,h in build['source_sha256'].items():assert sha(ROOT/p)==h
    evidence=ROOT/'evidence/quality_preview'/digest[:12];validation=read(evidence/'result.json');cuts=read(evidence/'black_cuts/result.json')
    assert validation['status']==cuts['status']=='pass'and validation['ROM_sha256']==cuts['ROM_sha256']==digest
    keys=read(evidence/'keypress_LCD/result.json');menu=read(evidence/'menu_regions/result.json')
    assert keys['status']==menu['status']=='pass'and keys['ROM_sha256']==menu['quality_preview_ROM_sha256']==digest
    assert keys['fully_black_frames']==keys['transient_or_torn_frames']==0
    assert sha(BASE_ZIP)==BASE_ZIP_SHA
    # Use the Linux filesystem for the many small files; deliver only verified
    # archives to the Windows mount. The old base ZIP already owns all inputs.
    stage=Path('/tmp')/('ruina_quality_release_'+digest[:12]);assert not stage.exists();stage.mkdir()
    print('Preparing a separate source project',flush=True)
    project=extract(BASE_ZIP,stage,SOURCE_NAME)
    selected=[Path('tools')/name for name in ('build_quality_preview.py','check_quality_preview.py','check_quality_black_cuts.py','check_quality_flicker.py','check_quality_menu_regions.py','gba_acceptance_probe.c','build_probe.py','capture_quality_baseline.py','make_quality_comparison.py','package_quality_preview.py','gba_fixture.py','drive_opening.py','project_env.py')]
    selected.append(Path('tests/quality_menu_fixture.c'))
    selected += [p.relative_to(ROOT)for p in(ROOT/'experiments/quality_preview').glob('*')if p.is_file()]
    for p in selected:
        if allowed(p):cp(ROOT/p,project/p)
    # Retain failed prototype reports with their own hashes and scope notes.
    for p in(ROOT/'evidence/quality_preview').rglob('*'):
        if p.is_file()and p.suffix in('.json','.log','.txt'):cp(p,project/p.relative_to(ROOT))
    guide='''废都物语 GBA · 开场画质预览局部刷新匹配工程（2026-10-22）

这个独立实验仅覆盖原版开头到首次地图。它不是全游戏直色移植版。
主运行工程仍为 v0.6.2；RGB555 预览源码位于 experiments/quality_preview/。
tools/build_quality_preview.py 替换渲染入口及投影，复用原剧情解释器与缓存资源。

在 Linux/WSL 安装 GNU Arm Embedded 工具链和 Python 3 后，在工程目录执行：
  python3 -S tools/build.py --incremental
  python3 -S tools/build_quality_preview.py
可设置 ARM_TOOLCHAIN_PREFIX。输出：
  build/废都物语_GBA_开篇开发验证版.gba（原 v0.6.2）
  build/fixtures/quality_preview/quality_preview.gba（本次画质预览）
不需要原 ZIP、字体、Pillow 或 NumPy 即可重建；缓存标题已附。
本次两种 ROM 均通过工程重建和实际源 ZIP 解压重建的逐字节一致检查。
原图逐像素测试另需你自己的原 ZIP、Pillow/NumPy 和 mGBA 开发库。
Windows 原生构建和实机未测试。本包不附工具链、ROM 或用户同名 SAV。

显示逻辑：GBA Mode 3，240×160，直接 RGB555。原尺寸模式显示原图裁切，
完整画面模式按统一比例缩小。头像直接绘制原始 48×48；全图浏览不改探索进度。
先在 CPU 内存画完再更新屏幕，普通重画不再压黑。保存功能在这个浏览目标中禁用，
节省的内存用作完整 RGB555 画面缓冲；普通 v0.6.2 保存功能不变。
选项上下仅画旧、新两行，列表滚动仅更新列表；取名光标仅画两个字格。
像素变化的行段才提交；背景或头像不变时不重复解码。剧情明确要求的黑屏仍保留。
这次仍以画质为主，所有图片解码/地图绘制的速度尚未优化完成。
预览不读写用户存档。首次地图只供浏览，不提供继续战斗或通关入口。
原素材自身的分辨率/细节以及 RGB555 限制仍存在，不能称为 PC 完全无损。

操作与证据见“开场画质预览说明.txt”和 evidence/quality_preview/。
其余 README/历史发布说明描述的是基础 v0.6.2，不能当成本预览的功能清单。
来源和许可证见 CREDITS.txt、LICENSE、third_party/。
'''
    (project/'工程使用说明.txt').write_text(guide,encoding='utf-8-sig')
    preview_guide='''废都物语 GBA · 开场画质预览局部刷新修正版（2026-10-22）

本版本专门看画质，从原游戏开头走到第一次地图展示为止。
使用原剧情，不附用户存档，不读写普通 SAV。原 v0.6.2 和旧存档未被替换。
保持原画质，修复普通按键重画时黑闪；准备新画面期间保留旧画面。
上下选择只更新两个选项行；翻动时更新列表；取名光标只更新两个字格。
增加/删除名字只更新姓名栏；换字库更新页签和字格。背景、头像不变就保留。
原剧情明确要求的黑屏切换继续保留。图片解码、地图绘制仍可能有等待。

如何查看
1. 用 GBA 模拟器打开 ROM，标题按 A。
2. 选“原像素画面”：原尺寸显示，可查看细节；或选“完整画面”：缩小看完整构图。
3. 按原游戏选出身、性别、头像、名字和难度。A 继续，B 返回。
   取名可 START 直接保留默认；只需看效果时推荐骑士的嫡子、男性、普通难度。
4. 对话中按 SELECT 隐藏文字查看原图，方向键浏览；B 或 SELECT 回到同一页文字。
5. 首次地图为浏览页：方向键滚动，SELECT 切换探索遮罩/完整底图，START 回标题。
   三角表示还能否浏览，不表示可通行。看完整底图不改变游戏探索或剧情状态。
   该页不能调查、战斗或继续通关；这是明确限定范围的画质样片。

画质方式
使用 Mode 3 直接 RGB555，不再把同屏图片拟合到共同的有限调色板。
插图可按原尺寸显示，头像保持原始 48×48。没有 AI 补画、锐化或虚构细节。
GBA 屏幕只有 240×160，原图超出屏幕要裁切浏览；完整模式仍需缩小。
原 RGB8 到 GBA RGB555 仍有精度损失，不能叫 PC 完全无损。
首次洞窟原素材只有 320×240；“原素材参考_不是GBA截图”是原尺寸源图导出，
用来辨别素材本身的细节上限，不是 GBA 截图。实际截图目录和对照图另列。

验证范围
四种原版出身 × 两种显示方式，共八条自然按键开场均到达首次地图。
检查约 45.8 万地图像素、7.4 万头像像素，与原素材对应 RGB555 值一致。
检查隐藏文本后返回原页、地图浏览不改游戏状态、回标题无残留遮罩。
开场黑屏切换已按实际模拟器 LCD 帧抽查。未计为全游戏、全剧情或实机通过。
普通按键逐帧检查无黑帧、无中间撕裂帧；另将八选项的滚动、循环选择画面
与原整屏重画逐像素哈希对照，结果一致。受控菜单测试与自然开场测试分开记录。
当前不报告整场游戏帧率，也不把这个试验视为性能优化完成。

匹配工程 ZIP 另附。基础源码保留 v0.6.2，本预览为独立构建目标。
'''
    (project/'开场画质预览说明.txt').write_text(preview_guide,encoding='utf-8-sig')
    print('Rebuilding staged base and RGB555 target without original archive or image libraries',flush=True)
    proof=rebuild(project,project/'画质预览工程重建日志.txt',digest);write(project/'画质预览工程重建校验.json',proof)
    # Only source/cached inputs and evidence are archived, never compiler outputs.
    files=[p.relative_to(project)for p in project.rglob('*')if p.is_file()and allowed(p)and p.name!='工程文件清单.json']
    manifest={'base_v062_ROM_sha256':BASE_SHA,'quality_preview_ROM_sha256':digest,'files':[{'path':str(p),'bytes':(project/p).stat().st_size,'sha256':sha(project/p)}for p in sorted(files)]}
    write(project/'工程文件清单.json',manifest);files.append(Path('工程文件清单.json'))
    source_zip=zip_folder(project,files)
    print('Checking actual source ZIP, then rebuilding both targets from a fresh extraction',flush=True)
    extracted=extract(source_zip,stage/'actual_zip_rebuild');checked=0
    for row in read(extracted/'工程文件清单.json')['files']:
        p=extracted/row['path'];assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],row['path'];checked+=1
    actual=rebuild(extracted,stage/'actual_ZIP_rebuild.log',digest)
    actual.update(source_ZIP_sha256=sha(source_zip),manifest_files_verified=checked,archive_CRC='pass',fresh_extraction=True)
    write(stage/'actual_ZIP_rebuild.json',actual)
    demo=stage/DEMO_NAME;demo.mkdir();cp(rom,demo/ROM_NAME);(demo/'试玩说明.txt').write_text(preview_guide,encoding='utf-8-sig')
    for p in(evidence/'comparison').rglob('*'):
        if p.is_file():cp(p,demo/'画质对照与原素材参考'/p.relative_to(evidence/'comparison'))
    gallery=evidence/'native/origin_1'
    for name in('title.png','dialogue_000.png','four_original_faces.png','dialogue_018.png','first_map.png','original_illustration.png','original_map_0_0.png','original_map_80_80.png'):
        cp(gallery/name,demo/'实际模拟器截图'/name)
    for src,name in((evidence/'result.json','开场八条流程验证.json'),(evidence/'black_cuts/result.json','剧情黑屏切换验证.json'),(evidence/'keypress_LCD/result.json','普通按键逐帧与局部刷新验证.json'),(evidence/'menu_regions/result.json','选项滚动对照验证.json'),(stage/'actual_ZIP_rebuild.json','实际工程ZIP重建校验.json'),(project/'画质预览工程重建校验.json','画质预览工程重建校验.json')):cp(src,demo/name)
    write(demo/'交付校验.json',{'scope':'opening through first map viewer only','ROM_sha256':digest,'ROM_bytes':rom.stat().st_size,'source_ZIP_sha256':sha(source_zip),'baseline_preserved_SHA256':BASE_SHA,'tests':'8 natural opening flows, source pixel comparisons, actual keypress LCD frames, incremental/reference menu comparison and explicit story black-cut observations passed','performance':'whole scene decoding not optimized yet','hardware':'not_run','whole_game':'not_run'})
    demo_zip=zip_folder(demo,[p.relative_to(demo)for p in demo.rglob('*')if p.is_file()])
    for p,h in build['source_sha256'].items():assert sha(ROOT/p)==h
    assert sha(rom)==digest and sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba')==BASE_SHA
    destinations=[ROOT/'交付',Path('/mnt/c/Users/APP/Downloads')]
    for folder in destinations:
        for name in(demo.name,source_zip.name,demo_zip.name):assert not(folder/name).exists(),str(folder/name)
    print('Verified; copying the new delivery without overwriting earlier releases',flush=True)
    for folder in destinations:
        folder.mkdir(exist_ok=True);shutil.copytree(demo,folder/demo.name)
        for archive in(source_zip,demo_zip):cp(archive,folder/archive.name);assert sha(folder/archive.name)==sha(archive)
        assert sha(folder/demo.name/ROM_NAME)==digest
    downloads=destinations[-1];result={'status':'delivered','UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'ROM':str(downloads/demo.name/ROM_NAME),'ROM_sha256':digest,'ROM_bytes':rom.stat().st_size,'DEMO_ZIP':str(downloads/demo_zip.name),'SOURCE_ZIP':str(downloads/source_zip.name),'SOURCE_ZIP_sha256':sha(source_zip),'actual_source_ZIP_rebuild':actual,'scope':'opening through first map viewer only','hardware':'not_run','full_game':'not_run'}
    write(ROOT/'evidence/quality_preview/delivery.json',result);print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
