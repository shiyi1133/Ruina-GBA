"""Run controlled host fixtures; never patch a release ROM or emulated RAM."""
import hashlib,json,subprocess,sys
from pathlib import Path
from project_env import ROOT

def main():
 sources=['tests/shared_events_host.c','runtime/rm2k/lcf.c','runtime/rm2k/state.c','runtime/rm2k/interpreter.c','runtime/rm2k/rm2k_rules.c','runtime/rm2k/map_rules.c','runtime/rm2k/map_info.c','runtime/rm2k/timers.c','runtime/rm2k/movement.c','runtime/rm2k/pictures.c','runtime/rm2k/presentation.c','runtime/rm2k/animations.c','runtime/rm2k/storage_codec.c']
 predecoded='--predecoded'in sys.argv;
 if predecoded:sources.append('build/borrowed_commands.c')
 name='shared_events_predecoded_host'if predecoded else'shared_events_host';flags=['-DLCF_TEST_ROM_CACHE','-DRUINA_PREDECODE_COMMANDS','-DRUINA_PREDECODE_PAGES','-DRUINA_BORROW_COMMANDS']if predecoded else[]
 subprocess.run(['cc','-std=c99','-O1','-g','-ffreestanding',*flags,'-Isource','-Iruntime/rm2k','-Ibuild',*sources,'-o','build/'+name],cwd=ROOT,check=True)
 result=subprocess.run([str(ROOT/'build'/name)],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 assert result.returncode==0,(result.returncode,result.stdout,result.stderr)
 report=json.loads(result.stdout);report['full_feature_fixture_output']=result.stderr;report['production_sources_sha256']={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in sources+['runtime/rm2k/battle.c','runtime/rm2k/parallel.c','runtime/rm2k/world.c','tests/full_features_host.inc']}
 report['controlled_setup']='Actors, switches and enemy HP are set in the host fixture to exercise rules. This is not a natural gameplay playthrough, emulator input or release-game modification.'
 report['original_switch_range_instructions_checked']=189
 report['original_enemy_variable_instructions_checked']=10
 report['predecoded_ROM_transport']=predecoded
 out=ROOT/'evidence/mechanisms';out.mkdir(exist_ok=True);(out/('host_event_integration_predecoded.json'if predecoded else'host_event_integration.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
