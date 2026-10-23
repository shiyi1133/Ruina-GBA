"""Fresh Linux extraction of the actual source ZIP, then byte-identical build."""
import hashlib,json,os,subprocess,sys,tempfile,time,zipfile
from pathlib import Path
from project_env import ROOT,arm_prefix

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(archive):
    archive=Path(archive).resolve();digest=sha(archive);production=json.loads((ROOT/'build/build_receipt.json').read_text())['sha256']
    out=ROOT/'evidence/balanced_optimization_20261023/archive_rebuild'/digest[:12];out.mkdir(parents=True,exist_ok=True)
    destination=Path(tempfile.mkdtemp(prefix='ruina-v07-archive-',dir='/tmp'));started=time.monotonic();compiler_version=subprocess.check_output([arm_prefix()+'gcc','--version'],text=True).splitlines()[0]
    with zipfile.ZipFile(archive)as z:
        assert z.testzip()is None
        names=z.namelist();roots={Path(n).parts[0]for n in names};assert len(roots)==1 and len(names)==len(set(names))
        assert all(not Path(n).is_absolute()and'..'not in Path(n).parts for n in names)
        assert not any(Path(n).suffix.lower()in('.gba','.elf','.o','.so','.exe')for n in names)
        manifest=json.loads(z.read(next(iter(roots))+'/工程文件清单.json'))
        assert {str(Path(next(iter(roots)))/r['path'])for r in manifest['files']}|{next(iter(roots))+'/工程文件清单.json'}==set(names)
        z.extractall(destination)
    project=destination/next(iter(roots));assert manifest['rom_sha256']==production
    for row in manifest['files']:
        p=project/row['path'];assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],row['path']
    env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_v07_original.zip',RUINA_FONT='/nonexistent_v07_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_v07_asset_python')
    with(out/'rebuild.log').open('w')as stream:
        subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=project,env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    rebuilt=project/'build/废都物语_GBA_开篇开发验证版.gba';assert sha(rebuilt)==production and sha(archive)==digest
    # Exercise the extracted public entry points in their new directory, with
    # original archive/font access still disabled. These use the bundled data
    # and PNG caches, plus explicitly external compiler/mGBA/Pillow tools.
    media=os.environ.get('RUINA_ASSET_PYTHON',sys.executable);smoke_env=env.copy();smoke_env['RUINA_ASSET_PYTHON']=media
    commands=[('build_probe',[sys.executable,'tools/build_probe.py']),('probe_file_IO_errors',[sys.executable,'tools/check_probe_save_io.py']),('attribution_page',[sys.executable,'tools/check_attribution.py']),('battle_menu_hierarchy',[sys.executable,'tools/check_battle_menu_navigation.py']),('new_game_battle_and_SAV',[sys.executable,'tools/check_phase_demo.py']),('original_recipes_and_title',[media,'tools/check_incremental_rooms.py']),('independent_cached_PNG_pixels',[media,'tools/check_balanced_rgb.py']),('save_and_cold_load_stack',[sys.executable,'tools/check_save_stack.py'])]
    checks=[]
    for label,command in commands:
        begin=time.monotonic()
        with(out/(label+'.log')).open('w')as stream:subprocess.run(command,cwd=project,env=smoke_env,stdout=stream,stderr=subprocess.STDOUT,check=True)
        checks.append({'name':label,'status':'pass','command':command,'host_seconds':time.monotonic()-begin})
    assert sha(rebuilt)==production and sha(archive)==digest
    record={'status':'pass','source_ZIP':archive.name,'source_ZIP_sha256':digest,'production_ROM_sha256':production,'rebuilt_ROM_sha256':sha(rebuilt),'byte_identical':True,'manifest_files_checked':len(manifest['files']),'fresh_extraction':str(destination),'original_archive_and_font':'disabled by nonexistent paths','cached_rebuild_asset_python':'disabled by nonexistent path','cached_rebuild_Python_site_packages':'disabled by -S','post_build_smoke_checks':checks,'smoke_dependencies':'external GNU Arm, mGBA development library, C compiler and Pillow/NumPy Python; no original archive/font','built_programs_in_input_ZIP':False,'host_seconds':time.monotonic()-started,'environment':'Linux/WSL; native Windows build not tested'}
    record['compiler_version']=compiler_version
    p=out/'result.json';p.write_text(json.dumps(record,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str(p.relative_to(ROOT))},ensure_ascii=False,indent=2));return record

if __name__=='__main__':print(json.dumps(verify(sys.argv[1]),ensure_ascii=False,indent=2))
