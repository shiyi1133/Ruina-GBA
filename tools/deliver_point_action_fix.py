"""Publish a scoped UI fix separately, with an actual source ZIP rebuild."""
import argparse, hashlib, json, os, shutil, subprocess, sys, zipfile
from pathlib import Path
from project_env import ROOT, arm_prefix
from deliver_optimization import inputs

VERSION = '0.6.1'
ROM_NAME = '废都物语_GBA_v0.6.1_地图调查修正版.gba'
DEMO_NAME = '废都物语_GBA_DEMO_v0.6.1_地图调查修正_20261022'
SOURCE_NAME = '废都物语_GBA_匹配工程_v0.6.1_20261022'
OUT = ROOT / 'evidence/point_action_v061'
NOTES = '地图调查修复_v0.6.1.txt'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def write(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2))


def progress(stage):
    write(OUT / 'packaging_progress.json', {'status': 'running', 'stage': stage})
    print(stage, flush=True)


def zip_folder(folder, paths):
    archive = folder.parent / (folder.name + '.zip')
    assert not archive.exists(), archive
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(set(paths)):
            z.write(folder / p, Path(folder.name) / p)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    return archive


def main():
    global VERSION, ROM_NAME, DEMO_NAME, SOURCE_NAME, OUT, NOTES
    parser = argparse.ArgumentParser()
    parser.add_argument('--common-names', action='store_true')
    common_names = parser.parse_args().common_names
    if common_names:
        VERSION = '0.6.2'
        ROM_NAME = '废都物语_GBA_v0.6.2_简易取名版.gba'
        DEMO_NAME = '废都物语_GBA_DEMO_v0.6.2_简易取名_20261022'
        SOURCE_NAME = '废都物语_GBA_匹配工程_v0.6.2_20261022'
        OUT = ROOT / 'evidence/common_names_v062'
        NOTES = '取名界面_v0.6.2.txt'
    OUT.mkdir(parents=True, exist_ok=True)
    rom = ROOT / 'build/废都物语_GBA_开篇开发验证版.gba'
    receipt = json.loads((ROOT / 'build/build_receipt.json').read_text())
    digest = sha(rom)
    assert digest == receipt['sha256'] and rom.stat().st_size <= 33554432
    refs = ['evidence/manual_investigation/latest_attempt.json',
            'evidence/phase_demo_20261021/latest_attempt.json',
            'evidence/hardware_scroll/navigation/latest_attempt.json',
            'evidence/cursor_flash/latest_attempt.json']
    if common_names:
        refs = ['evidence/name_input_v062/latest_attempt.json', 'evidence/naming_cut/latest_attempt.json'] + refs
    reports = []
    for ref in refs:
        p = Path(json.loads((ROOT / ref).read_text())['report'])
        report = json.loads((ROOT / p).read_text())
        assert report['status'] == 'pass' and report['rom_sha256'] == digest, p
        reports.append(p)
    validation = {'status': 'pass', 'ROM_sha256': digest, 'reports': [str(p) for p in reports],
                  'scope': 'manual/local A, L/R routing, camera browse, menu, ordinary SAV cold load, opening/first victory, 1650 intermediate LCD frames',
                  'full_v06_suite_rerun': False, 'whole_campaign': 'not_run', 'physical_hardware': 'not_run'}
    if common_names:
        validation['scope'] = '20 surnames/30 given-name characters and all 50 glyphs, editing/restore/limits, four origins naming and black cuts; inherited manual A, routing, opening/first victory, SAV and 1650 LCD frames retested'
    write(OUT / 'current_validation.json', validation)
    progress('verify original source archive and expand matching project')
    original = json.loads((ROOT / 'evidence/optimization_20261022/release_preparation.json').read_text())
    source_v06 = Path(original['source_zip'])
    assert sha(source_v06) == original['source_zip_sha256']
    if common_names:
        prior = json.loads((ROOT / 'evidence/point_action_v061/delivery.json').read_text())
        source_v06 = Path(prior['SOURCE_ZIP'])
        prior_check = json.loads((ROOT / 'evidence/point_action_v061/actual_ZIP_rebuild.log').read_text())
        assert sha(source_v06) == prior_check['source_ZIP_sha256']
    stage = ROOT / 'build' / (('common_names_v062_' if common_names else 'point_action_v061_') + digest[:12])
    stage.mkdir(exist_ok=False)
    extracted = stage / 'base_archive'
    with zipfile.ZipFile(source_v06) as z:
        assert z.testzip() is None
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        roots = {Path(n).parts[0] for n in z.namelist()}
        assert len(roots) == 1
        z.extractall(extracted)
    project = stage / SOURCE_NAME
    (extracted / next(iter(roots))).rename(project)
    extracted.rmdir()
    old_manifest = json.loads((project / '工程文件清单.json').read_text())
    old_hashes = {x['path']: x['sha256'] for x in old_manifest['files']}
    progress('overlay current source and cached build inputs')
    selected = inputs() + [Path(NOTES)]
    snapshot = {str(p): sha(ROOT / p) for p in selected}
    for p in selected:
        if old_hashes.get(str(p)) != snapshot[str(p)]:
            (project / p).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / p, project / p)
    wanted = set()
    for p in reports:
        wanted.add(p)
        wanted.update(x.relative_to(ROOT) for x in (ROOT / p).parent.rglob('*') if x.is_file())
    wanted.update(x.relative_to(ROOT) for x in (ROOT / 'evidence/manual_investigation').rglob('*') if x.is_file())
    wanted.update(x.relative_to(ROOT) for x in (ROOT / 'evidence').glob('manual*regression*.log'))
    wanted.add(Path('evidence/manual_investigation_baseline.log'))
    wanted.add(Path('evidence/manual_investigation_fixed.log'))
    wanted.add(Path('evidence/point_action_v061/current_validation.json'))
    wanted.add((OUT / 'current_validation.json').relative_to(ROOT))
    if common_names:
        wanted.add(Path('evidence/name_input_v062/font_extension.json'))
        wanted.update(p.relative_to(ROOT) for p in (ROOT / 'evidence/name_input_v062').glob('*.log'))
    for p in wanted:
        if p.suffix.lower() not in ('.json', '.png', '.txt', '.log', '.sav'):
            continue
        (project / p).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / p, project / p)
    (project / '工程使用说明.txt').write_text(
        f'匹配工程 v{VERSION}（2026-10-22）\n\n'
        f'本版变更和操作见“{NOTES}”。\n'
        'Linux/WSL、Python 3、外部 GNU Arm 工具链：python3 tools/build.py --incremental\n'
        '缓存素材已附，重建不需要原 ZIP、系统字体或 Python 图像库。README.txt 说明完整依赖和限制。\n'
        '工程重建校验.json 为本版独立重建结果；试玩包另附实际 ZIP 解压后的第二次重建校验。\n'
        '原 v0.6 验证报告保留其原 ROM 哈希，不冒充本版全项重跑。\n'
        f'本版检查入口为 {OUT.relative_to(ROOT)}/current_validation.json。\n'
        '完整通关、全部支线/结局和 GBA 实机未验收；不能宣称完全达到 PC 原版画质/性能。\n'
        'history/ 和 evidence/ 的 SAV 是测试材料，不要当作新游戏同名存档。\n', encoding='utf-8-sig')
    progress('clean build from the matching source project')
    env = os.environ.copy()
    env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(), RUINA_SOURCE_ARCHIVE='/nonexistent_v061_original.zip',
               RUINA_FONT='/nonexistent_v061_font.ttf', RUINA_ASSET_PYTHON='/nonexistent_v061_asset_python')
    with (project / '工程重建日志.txt').open('w') as output:
        subprocess.run([sys.executable, '-S', 'tools/build.py', '--incremental'], cwd=project, env=env,
                       stdout=output, stderr=subprocess.STDOUT, check=True)
    assert sha(project / 'build/废都物语_GBA_开篇开发验证版.gba') == digest
    assert all(sha(ROOT / p) == h for p, h in snapshot.items()), 'Source changed during release preparation'
    rebuild = {'status': 'pass', 'ROM_sha256': digest, 'byte_identical': True,
               'original_archive_and_font': 'disabled', 'Python_site_packages': 'disabled by -S',
               'environment': 'Linux/WSL; external GNU Arm toolchain; native Windows not tested'}
    write(project / '工程重建校验.json', rebuild)
    progress('create the source ZIP and rebuild its actual fresh extraction')
    banned = ('.gba', '.elf', '.o', '.so', '.exe', '.pyc', '.su')
    paths = [p.relative_to(project) for p in project.rglob('*') if p.is_file()
             and p.suffix.lower() not in banned and '__pycache__' not in p.parts
             and p.name != '工程文件清单.json']
    write(project / '工程文件清单.json', {'rom_sha256': digest, 'files': [
        {'path': str(p), 'bytes': (project / p).stat().st_size, 'sha256': sha(project / p)} for p in sorted(paths)]})
    source_zip = zip_folder(project, paths + [Path('工程文件清单.json')])
    with (OUT / 'actual_ZIP_rebuild.log').open('w') as output:
        subprocess.run([sys.executable, 'tools/verify_optimization_archive.py', str(source_zip)], cwd=ROOT,
                       stdout=output, stderr=subprocess.STDOUT, check=True)
    archive_report = json.loads((ROOT / json.loads((ROOT / 'evidence/optimization_20261022/archive_rebuild/latest_attempt.json').read_text())['report']).read_text())
    assert archive_report['source_ZIP_sha256'] == sha(source_zip) and archive_report['production_ROM_sha256'] == digest
    progress('assemble separate DEMO, then copy and verify delivery files')
    demo = stage / DEMO_NAME
    demo.mkdir()
    shutil.copy2(rom, demo / ROM_NAME)
    shutil.copy2(ROOT / NOTES, demo / '试玩说明.txt')
    with (demo / '试玩说明.txt').open('a', encoding='utf-8') as output:
        output.write('\n其它操作：START 系统菜单，A 确定、B 返回；标题“音乐欣赏”试听 105 首配乐。\n'
                     '欣赏页面上下选曲、A 播放/暂停、左右或 L/R 换曲、START 切换两种简化音色。\n'
                     'MIDI 在游戏内进一步简化；本版图像与声音资源沿用 v0.6。当前版本可能还有问题。\n')
    for ref in reports[:2]:
        for p in (ROOT / ref).parent.glob('*.png'):
            if p.name != 'failed.png':
                destination = demo / '实际试玩截图' / p.name
                destination.parent.mkdir(exist_ok=True)
                shutil.copy2(p, destination)
    write(demo / '修复验证.json', validation)
    write(demo / '工程ZIP重建校验.json', archive_report)
    write(demo / '交付校验.json', {'version': VERSION, 'ROM': ROM_NAME, 'ROM_sha256': digest,
                                  'ROM_bytes': rom.stat().st_size, 'source_ZIP_sha256': sha(source_zip),
                                  'full_campaign': 'not_run', 'hardware': 'not_run'})
    assert not list(demo.rglob('*.sav'))
    demo_zip = zip_folder(demo, [p.relative_to(demo) for p in demo.rglob('*') if p.is_file()])
    for directory in (ROOT / '交付', Path('/mnt/c/Users/APP/Downloads')):
        assert not (directory / DEMO_NAME).exists()
        assert not (directory / demo_zip.name).exists() and not (directory / source_zip.name).exists()
    for directory in (ROOT / '交付', Path('/mnt/c/Users/APP/Downloads')):
        shutil.copytree(demo, directory / DEMO_NAME)
        for archive in (source_zip, demo_zip):
            shutil.copy2(archive, directory / archive.name)
            assert sha(directory / archive.name) == sha(archive)
        assert sha(directory / DEMO_NAME / ROM_NAME) == digest
    downloads = Path('/mnt/c/Users/APP/Downloads')
    result = {'status': 'delivered', 'ROM_sha256': digest, 'ROM': str(downloads / DEMO_NAME / ROM_NAME),
              'DEMO_ZIP': str(downloads / demo_zip.name), 'SOURCE_ZIP': str(downloads / source_zip.name),
              'source_rebuild_byte_identical': True, 'originals_and_saves': 'preserved'}
    write(OUT / 'delivery.json', result)
    write(OUT / 'packaging_progress.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
