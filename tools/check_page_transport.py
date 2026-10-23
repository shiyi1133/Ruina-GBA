"""Old parser selection versus predecoded immutable page data, live state."""
import hashlib,json,subprocess
from project_env import ROOT

def main():
 sources=['tests/page_transport_parity_host.c','runtime/rm2k/lcf.c','runtime/rm2k/state.c','runtime/rm2k/interpreter.c','runtime/rm2k/rm2k_rules.c','runtime/rm2k/map_rules.c','runtime/rm2k/map_info.c','runtime/rm2k/timers.c','runtime/rm2k/movement.c','runtime/rm2k/pictures.c','runtime/rm2k/presentation.c','runtime/rm2k/animations.c','runtime/rm2k/storage_codec.c'];target=ROOT/'build/page_transport_host'
 subprocess.run(['cc','-std=c99','-O2','-ffreestanding','-DLCF_TEST_ROM_CACHE','-DRUINA_PREDECODE_COMMANDS','-DRUINA_PREDECODE_PAGES','-Isource','-Iruntime/rm2k','-Ibuild',*sources,'-o',str(target)],cwd=ROOT,check=True);p=subprocess.run([str(target)],cwd=ROOT,capture_output=True,text=True);assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
 report=json.loads(p.stdout);report['kind']='controlled host differential, original bytecode and page spans; no emulated RAM edits';report['sources_sha256']={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in sources+['build/pages.bin','build/original_lcf.bin']};out=ROOT/'evidence/optimization_20261022/page_transport';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
