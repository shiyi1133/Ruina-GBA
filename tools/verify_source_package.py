"""Rebuild the delivered source ZIP without the user's original ZIP or font.
Requires the external ARM toolchain; verifies all packaged source hashes first.
The rebuilt ROM is not used to replace the separately play-tested artifact.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,zipfile
from project_env import ROOT

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 package=Path(sys.argv[1])if len(sys.argv)>1 else ROOT/'交付/v0.2/废都物语_GBA_兼容框架工程_v0.2.zip'
 expected=json.loads((ROOT/'acceptance_receipt.json').read_text())['rom_sha256']
 with tempfile.TemporaryDirectory(prefix='ruina-source-rebuild-')as tmp:
  tmp=Path(tmp)
  with zipfile.ZipFile(package)as archive:
   assert archive.testzip()is None
   assert all(not Path(n).is_absolute() and '..'not in Path(n).parts for n in archive.namelist())
   archive.extractall(tmp)
  project=tmp/'废都物语_GBA章节样版'
  manifest=json.loads((project/'source_manifest.json').read_text())
  for row in manifest['files']:assert sha(project/row['path'])==row['sha256'],row['path']
  env=os.environ.copy();env['RUINA_SOURCE_ARCHIVE']=str(tmp/'no_original_archive.zip');env['RUINA_FONT']=str(tmp/'no_font.ttf')
  result=subprocess.run([sys.executable,'tools/build.py','--incremental'],cwd=project,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
  assert result.returncode==0,result.stdout
  actual=sha(project/'build/废都物语_GBA_开篇开发验证版.gba');assert actual==expected,(actual,expected,result.stdout)
  report={'status':'pass','kind':'fresh source ZIP extraction and cached-input rebuild with external ARM toolchain','source_zip':package.name,'source_zip_sha256':sha(package),'source_manifest_entries_verified':len(manifest['files']),'original_user_zip_available_to_build':False,'source_font_available_to_build':False,'network_used_by_build':False,'rebuilt_rom_sha256':actual,'matches_play_tested_rom':True,'rebuild_log':result.stdout,'hardware':'not_run'}
 out=package.parent;path=out/'源码包重建校验.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
 receipt_path=out/'交付校验.json';receipt=json.loads(receipt_path.read_text());receipt['offline_source_zip_rebuild']={'status':'pass','report':path.name,'sha256':sha(path),'source_zip_sha256':report['source_zip_sha256'],'matches_play_tested_rom':True}
 receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2));download=Path(receipt['download_directory'])
 for p in [path,receipt_path]:shutil.copyfile(p,download/p.name);assert sha(p)==sha(download/p.name)
 print(json.dumps({k:v for k,v in report.items()if k!='rebuild_log'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
