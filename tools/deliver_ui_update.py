"""Package scoped v0.7.1 UI changes; prior v0.7 broad QA stays historical."""
import hashlib, json, os, shutil, subprocess, sys, tempfile, zipfile
from pathlib import Path
from project_env import ROOT, arm_prefix
from deliver_optimization import inputs

VERSION='0.7.1'
OUT=ROOT/'evidence/ui_v071'
SOURCE_NAME='废都物语_GBA_匹配工程_v0.7.1_20261023'
DEMO_NAME='废都物语_GBA_v0.7.1_取名与操作说明版_20261023'
ROM_NAME='废都物语_GBA_v0.7.1_取名与操作说明版.gba'
NOTES='取名与操作说明_v0.7.1.txt'


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads((ROOT/p).read_text())
def write(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def progress(value):
    write(OUT/'packaging_progress.json',{'status':'running','stage':value});print(value,flush=True)
def archive(folder,paths):
    path=folder.parent/(folder.name+'.zip');assert not path.exists(),path
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(set(paths)):z.write(folder/p,Path(folder.name)/p)
    with zipfile.ZipFile(path) as z:assert z.testzip() is None
    return path


def main():
    receipt=read('build/build_receipt.json');rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=sha(rom)
    assert receipt['version']==VERSION and receipt['sha256']==digest and rom.stat().st_size<=33554432
    assert all(sha(ROOT/p)==h for p,h in receipt['compiler_inputs_sha256'].items())
    original=read('history/ui_v071_before/build/build_receipt.json')
    changed=[p for p,h in receipt['compiler_inputs_sha256'].items() if original['compiler_inputs_sha256'].get(p)!=h]
    assert set(changed)=={'source/maps.c','platform/gba/event_input.c','build/assets.c','build/assets.h'},changed
    font=read('evidence/ui_v071/font_extension.json')
    assert font['status']=='pass' and font['existing_glyph_rows_unchanged'] and font['non_font_asset_data_unchanged']
    refs=[Path(read(ref)['report']) for ref in ['evidence/ui_v071/naming_latest.json','evidence/ui_v071/controls_latest.json','evidence/naming_cut/latest_attempt.json','evidence/phase_demo_20261021/latest_attempt.json']]
    refs.append(Path(f'evidence/balanced_optimization_20261023/{digest[:12]}/battle_menu_navigation/result.json'))
    for ref in refs:
        data=read(ref);assert data['status']=='pass' and (data.get('rom_sha256') or data.get('production_ROM_sha256'))==digest,ref
    assert {x['origin'] for x in read(refs[2])['origins']}=={1,2,3,4}
    validation={'status':'pass','version':VERSION,'ROM_sha256':digest,'reports':[str(p) for p in refs],
        'scope':'All 221 name choices exact LCD glyphs; 30 surnames/100 given characters/case/digits/29 symbols; paging/limits/deletion; mixed-name ordinary SRAM cold-load; five help pages, 35 exact LCD text lines, nested B return and state preservation in new game and campaign SAV; four original openings; first original battle and victory; battle menu hierarchy/resources/LCD stability.',
        'changed_compiler_inputs':changed,'font_extension':str((OUT/'font_extension.json').relative_to(ROOT)),
        'unchanged':'Every other compiled source, original LCF, graphics, audio and save implementation; Game stays 39704 bytes, v5 SRAM format.',
        'inherited_v07_report':'evidence/balanced_optimization_20261023/final_acceptance.json',
        'inherited_report_ROM_sha256':original['sha256'],'whole_v07_suite_rerun':False,'whole_music_rerun':False,
        'test_observation_note':'Live selected-point marker animation is excluded from whole-map static hash assertions; every return frame is pixel-checked outside its actual 16x16 sprite rectangle. Earlier overly strict assertion failures are preserved.',
        'physical_hardware':'not_run','full_campaign':'not_run'}
    write(OUT/'current_validation.json',validation)
    prior=read('evidence/balanced_optimization_20261023/release_preparation.json')
    baseline=Path(prior['source_zip']);assert sha(baseline)==prior['source_zip_sha256']
    stage=Path(tempfile.mkdtemp(prefix='ruina-v071-release-',dir='/tmp'));extracted=stage/'base';progress('Extract verified v0.7 source archive')
    with zipfile.ZipFile(baseline) as z:
        assert z.testzip() is None
        roots={Path(n).parts[0] for n in z.namelist()};assert len(roots)==1
        assert all(not Path(n).is_absolute() and '..' not in Path(n).parts for n in z.namelist())
        z.extractall(extracted)
    project=stage/SOURCE_NAME;(extracted/next(iter(roots))).rename(project);extracted.rmdir()
    old_hashes={row['path']:row['sha256'] for row in json.loads((project/'工程文件清单.json').read_text())['files']}
    selected=inputs()+[Path('README.md'),Path(NOTES),Path('history/ui_v071_before/build/build_receipt.json'),Path('history/ui_v071_before/source/maps.c'),Path('history/ui_v071_before/platform/gba/event_input.c')]+[p.relative_to(ROOT) for p in (ROOT/'docs').glob('*.png')]
    selected=sorted(set(selected));snapshot={str(p):sha(ROOT/p) for p in selected}
    progress('Overlay changed sources and cached font, preserving prior evidence')
    for p in selected:
        if old_hashes.get(str(p))!=snapshot[str(p)]:
            dest=project/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,dest)
    wanted=set()
    for ref in refs:
        wanted.update(p.relative_to(ROOT) for p in (ROOT/ref).parent.rglob('*') if p.is_file())
    wanted.update(p.relative_to(ROOT) for p in OUT.rglob('*') if p.is_file() and p.name not in ('packaging_progress.json','delivery.log') and not p.name.startswith(('delivery','public_source')))
    for p in sorted(wanted):
        if p.suffix.lower() not in ('.json','.png','.txt','.log','.sav'):continue
        dest=project/p;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/p,dest)
    (project/'工程使用说明.txt').write_text('''匹配工程 v0.7.1（2026-10-23）

本次新增扩充取名与 B 菜单操作说明。操作见“取名与操作说明_v0.7.1.txt”。
构建：Linux/WSL、Python 3、外部 GNU Arm 工具链，执行 python3 tools/build.py --incremental。
ARM_TOOLCHAIN_PREFIX 可指定 arm-none-eabi- 前缀。转换资源已附，无需原 ZIP、系统字体或图像库。
工程重建校验.json 记录独立重建；交付包另核对实际源码 ZIP 的新解压重建。
本次检查入口：evidence/ui_v071/current_validation.json。
命名与操作说明专测：tools/check_common_names.py、tools/check_controls_help.py。
按键测试另需外部 mGBA 开发库、Pillow/NumPy、C 编译器，详见 README.txt。
v0.7 原报告保持原哈希，未冒充本次整曲或全部回归重跑。
本包不含工具链、原游戏 ZIP、ROM 或旧版对比 ROM；缓存为编译输入。
history/、evidence/ 的 SAV 为测试材料，不要当作新游戏的同名存档。
完整自然通关、全部结局、GBA 实机以及 Windows 原生构建尚未验收。
来源与许可证见 CREDITS.txt、LICENSE、third_party/。
''',encoding='utf-8-sig')
    progress('Build matching project with original archive, font and Python packages disabled')
    env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_v071_original.zip',RUINA_FONT='/nonexistent_v071_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_v071_asset_python')
    with (project/'工程重建日志.txt').open('w') as stream:
        subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    assert sha(project/'build/废都物语_GBA_开篇开发验证版.gba')==digest
    assert all(sha(ROOT/p)==h for p,h in snapshot.items()),'Source changed during packaging'
    write(project/'工程重建校验.json',{'status':'pass','ROM_sha256':digest,'byte_identical':True,'original_archive_and_font':'disabled','Python_site_packages':'disabled by -S','environment':'Linux/WSL, external GNU Arm'})
    banned={'.gba','.elf','.o','.so','.exe','.pyc','.su','.map'}
    paths=[p.relative_to(project) for p in project.rglob('*') if p.is_file() and p.suffix.lower() not in banned and '__pycache__' not in p.parts and p.name!='工程文件清单.json']
    write(project/'工程文件清单.json',{'rom_sha256':digest,'files':[{'path':str(p),'bytes':(project/p).stat().st_size,'sha256':sha(project/p)} for p in sorted(paths)]})
    source_zip=archive(project,paths+[Path('工程文件清单.json')]);progress('Rebuild actual fresh source ZIP and run eight independent playable smoke checks')
    from verify_balanced_archive import verify
    rebuilt=verify(source_zip);assert rebuilt['byte_identical'] and rebuilt['production_ROM_sha256']==digest
    write(OUT/'actual_ZIP_rebuild.json',rebuilt)
    demo=stage/DEMO_NAME;demo.mkdir();shutil.copy2(rom,demo/ROM_NAME);shutil.copy2(ROOT/NOTES,demo/'试玩说明.txt')
    shutil.copytree(ROOT/'docs',demo/'实际试玩截图')
    controls=ROOT/refs[1].parent
    for p in controls.glob('controls_*.png'):shutil.copy2(p,demo/'实际试玩截图'/p.name)
    write(demo/'本次验证.json',validation);write(demo/'源码ZIP重建校验.json',rebuilt)
    write(demo/'交付校验.json',{'version':VERSION,'ROM':ROM_NAME,'ROM_sha256':digest,'ROM_bytes':rom.stat().st_size,'source_ZIP_sha256':sha(source_zip),'full_campaign':'not_run','physical_hardware':'not_run'})
    demo_zip=archive(demo,[p.relative_to(demo) for p in demo.rglob('*') if p.is_file()]);assert not list(demo.rglob('*.sav'))
    progress('Fresh extraction of renamed playable demo, new game and ordinary SRAM cold load')
    from check_balanced_distribution import verify_demo
    distribution=verify_demo(demo_zip,digest);write(OUT/'distribution_smoke.json',distribution)
    combined=stage/'废都物语_GBA_v0.7.1_工程与试玩ROM_20261023.zip'
    with zipfile.ZipFile(combined,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        with zipfile.ZipFile(source_zip) as src:
            root=src.namelist()[0].split('/')[0]+'/'
            for n in src.namelist():z.writestr('工程/'+n[len(root):],src.read(n))
        for p in sorted(demo.rglob('*')):
            if p.is_file():z.write(p,Path('试玩')/p.relative_to(demo))
        z.writestr('阅读说明.txt','试玩/ 中为可直接打开的 GBA ROM；工程/ 为匹配源码和转换缓存。\n取名扩充和操作说明见试玩说明，构建和验证见工程使用说明。\n')
        z.writestr('发布包核对.json',json.dumps({'ROM_sha256':digest,'source_ZIP_rebuild_byte_identical':True,'source_ZIP_sha256':sha(source_zip),'demo_ZIP_sha256':sha(demo_zip),'renamed_demo_new_game_and_SAV':'pass'},ensure_ascii=False,indent=2))
    with zipfile.ZipFile(combined) as z:assert z.testzip() is None
    for directory in (ROOT/'交付',Path('/mnt/c/Users/APP/Downloads')):
        assert not (directory/DEMO_NAME).exists()
        assert not any((directory/p.name).exists() for p in (source_zip,demo_zip,combined))
    for directory in (ROOT/'交付',Path('/mnt/c/Users/APP/Downloads')):
        shutil.copytree(demo,directory/DEMO_NAME)
        for p in (source_zip,demo_zip,combined):shutil.copy2(p,directory/p.name);assert sha(directory/p.name)==sha(p)
        assert sha(directory/DEMO_NAME/ROM_NAME)==digest
    downloads=Path('/mnt/c/Users/APP/Downloads')
    result={'status':'delivered','version':VERSION,'ROM_sha256':digest,'ROM':str(downloads/DEMO_NAME/ROM_NAME),'SOURCE_ZIP':str(downloads/source_zip.name),'DEMO_ZIP':str(downloads/demo_zip.name),'COMBINED_ZIP':str(downloads/combined.name),'source_zip_sha256':sha(source_zip),'demo_zip_sha256':sha(demo_zip),'combined_sha256':sha(combined),'stage':str(stage),'project':str(project),'source_ZIP_rebuild_byte_identical':True,'old_releases_and_saves':'preserved','physical_hardware':'not_run','full_campaign':'not_run'}
    write(OUT/'delivery.json',result);write(OUT/'packaging_progress.json',result);print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
