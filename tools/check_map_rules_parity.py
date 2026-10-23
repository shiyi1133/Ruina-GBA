"""Current map movement/coordinate caches against pre-optimization rules."""
import hashlib,json,subprocess
from project_env import ROOT

def main():
 sources=['tests/map_rules_parity_host.c','runtime/rm2k/lcf.c','runtime/rm2k/state.c','runtime/rm2k/interpreter.c','runtime/rm2k/rm2k_rules.c','runtime/rm2k/map_rules.c','runtime/rm2k/map_info.c','runtime/rm2k/timers.c','runtime/rm2k/movement.c','runtime/rm2k/pictures.c','runtime/rm2k/presentation.c','runtime/rm2k/animations.c','runtime/rm2k/storage_codec.c'];target=ROOT/'build/map_rules_parity_host'
 bindings={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in sources+['tests/reference/map_rules_20261021.c','runtime/rm2k/world.c','build/original_lcf.bin']}
 subprocess.run(['cc','-std=c99','-O2','-ffreestanding','-DLCF_TEST_ROM_CACHE','-DRUINA_PREDECODE_COMMANDS','-DRUINA_PREDECODE_PAGES','-Isource','-Iruntime/rm2k','-Ibuild',*sources,'-o',str(target)],cwd=ROOT,check=True)
 p=subprocess.run([str(target)],cwd=ROOT,capture_output=True,text=True);assert p.returncode==0,(p.returncode,p.stdout,p.stderr);report=json.loads(p.stdout);report['kind']='controlled host differential; unchanged original map data; original position/collision/terrain path compared to current sparse and cached queries';report['sources_sha256']=bindings;report['source_changed_during_run']=any(hashlib.sha256((ROOT/s).read_bytes()).hexdigest()!=h for s,h in bindings.items());assert not report['source_changed_during_run'];out=ROOT/'evidence/optimization_20261022/map_rules';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
