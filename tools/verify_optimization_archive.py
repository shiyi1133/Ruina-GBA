"""Extract the actual source ZIP and rebuild without original art or modules."""
import hashlib,json,os,subprocess,sys,time,zipfile
from project_env import ROOT,arm_prefix

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 from pathlib import Path
 archive=Path(sys.argv[1]);digest=sha(archive);receipt=json.loads((ROOT/'build/build_receipt.json').read_text());out=ROOT/'evidence/optimization_20261022/archive_rebuild'/digest[:12];out.mkdir(parents=True,exist_ok=True)
 destination=ROOT/'build'/('archive_rebuild_'+digest[:12]+'_'+str(time.time_ns()));destination.mkdir();start=time.monotonic()
 with zipfile.ZipFile(archive)as z:
  assert z.testzip()is None;names=z.namelist();roots={Path(n).parts[0]for n in names};assert len(roots)==1
  assert all(not Path(n).is_absolute()and'..'not in Path(n).parts for n in names)
  assert not any(Path(n).suffix in('.gba','.elf','.o','.so','.exe')for n in names),'Source ZIP contains built programs'
  z.extractall(destination)
 project=destination/next(iter(roots));manifest=json.loads((project/'工程文件清单.json').read_text());assert manifest['rom_sha256']==receipt['sha256']
 for row in manifest['files']:assert sha(project/row['path'])==row['sha256'],row['path']
 env=os.environ.copy();env.update(ARM_TOOLCHAIN_PREFIX=arm_prefix(),RUINA_SOURCE_ARCHIVE='/nonexistent_archive_rebuild_original.zip',RUINA_FONT='/nonexistent_archive_rebuild_font.ttf',RUINA_ASSET_PYTHON='/nonexistent_archive_rebuild_asset_python')
 with(out/'rebuild.log').open('w')as output:subprocess.run([sys.executable,'-S','tools/build.py','--incremental'],cwd=project,env=env,stdout=output,stderr=subprocess.STDOUT,check=True)
 rebuilt=project/'build/废都物语_GBA_开篇开发验证版.gba';assert sha(rebuilt)==receipt['sha256'];assert sha(archive)==digest
 report={'status':'pass','actual_source_ZIP':archive.name,'source_ZIP_sha256':digest,'source_manifest_files_checked':len(manifest['files']),'ROM_sha256':sha(rebuilt),'production_ROM_sha256':receipt['sha256'],'byte_identical':True,'fresh_extraction':True,'original_archive_and_font':'disabled by nonexistent paths','Python_site_packages':'disabled by -S','compiled_objects_in_input_ZIP':False,'wall_seconds':time.monotonic()-start,'environment':'Linux/WSL, external GNU Arm toolchain; native Windows not tested'}
 (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
