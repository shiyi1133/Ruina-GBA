"""Package only reports matching the final ROM; retain incomplete boundaries."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from project_env import ROOT
VERSION='0.2'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def collect_commands(value,output):
 if isinstance(value,list):
  for row in value:collect_commands(row,output)
 elif isinstance(value,dict):
  for key,row in value.items():
   if key=='commands' or key.endswith('_commands') or key.startswith('commands_') or key=='keys_and_read_only_observations':
    if isinstance(row,list):output.extend(row)
   else:collect_commands(row,output)
def main():
 rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=sha(rom)
 out=ROOT/'交付'/('v'+VERSION);out.mkdir(parents=True,exist_ok=True)
 checks={
  'chapter_main_route':'evidence/chapter_progress/progress.json',
  'ordinary_sav_cold_load':'evidence/save_cold_load/result.json',
  'defeat_new_game_and_corruption':'evidence/recovery/result.json',
  'original_menus_and_v2_migration':'evidence/refactor/menus/result.json',
  'audio_actual_output':'evidence/audio/result.json',
  'audio_complete_loop':'evidence/audio/loop_result.json',
 }
 for origin in [1,2,3,4]:checks['opening_first_battle_origin_'+str(origin)]=f'evidence/first_battle_origin_{origin}/result.json'
 checks['automatic_mage_battle']='evidence/first_battle_origin_3_auto/result.json'
 rows={};all_commands=[]
 for key,path in checks.items():
  r=json.loads((ROOT/path).read_text());assert r['rom_sha256']==digest,(key,'wrong ROM')
  assert (r['chapter_complete'] if key=='chapter_main_route' else r['status']=='pass'),(key,r)
  rows[key]={'status':'pass','report':path,'report_sha256':sha(ROOT/path)}
  collect_commands(r,all_commands)
 allowed={'frames','read','shot','savecopy','record','stop'}
 assert all(isinstance(c,str) and c.split()[0]in allowed for c in all_commands)
 raw=rom.read_bytes();assert len(raw)<=32*1024*1024 and raw[178]==0x96
 assert ((-sum(raw[160:189])-0x19)&255)==raw[189]
 integrity=json.loads((ROOT/'evidence/native_data_verification.log').read_text());assert integrity['status']=='pass'
 rules=json.loads((ROOT/'evidence/refactor/rule_parity.json').read_text());assert rules['status']=='pass'
 assert rules['native_source_sha256']==sha(ROOT/'runtime/rm2k/rm2k_rules.c')
 audit=json.loads((ROOT/'evidence/refactor/compatibility_audit.json').read_text())
 assert audit['status']=='audit_complete' and audit['source_lock_verified'] and audit['command_ids_match_pinned_liblcf']
 lock_sha=sha(ROOT/'third_party/sources.lock.json');assert rules['upstream_lock_sha256']==lock_sha
 build=json.loads((ROOT/'build/build_receipt.json').read_text());assert build['sha256']==digest and build['upstream_lock_sha256']==lock_sha
 production=[]
 for directory in ['source','runtime','platform','tools','third_party']:
  production.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
 dump(ROOT/'source_manifest.json',{'kind':'v0.2 delivered source and pinned references','files':[{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}for p in sorted(production)]})
 report={
  'version':VERSION,'artifact':'废都物语_GBA_首章试玩_v0.2.gba','rom_sha256':digest,'rom_bytes':len(raw),
  'source_archive_sha256':'589a0adb0f710200f19522e19a96fa394f67aabd40100edd8664bb60f5e509c4',
  'kind':'native GBA RM2000 compatibility framework with Ruina chapter adapter',
  'complete_EasyRPG_port':False,'full_game_port':False,
  'scope':'骑士男性默认角色、普通难度：从新游戏到瀑布洞窟首个CP、领取原奖励并返城；另验收指定称号、料理及调和事件',
  'main_route':'pass','checks':rows,
  'host_checks':{
   'unchanged_original_data':{'status':'pass','report':'evidence/native_data_verification.log','sha256':sha(ROOT/'evidence/native_data_verification.log'),'summary':integrity},
   'pinned_upstream_rules':{'status':'pass','report':'evidence/refactor/rule_parity.json','sha256':sha(ROOT/'evidence/refactor/rule_parity.json'),'comparisons':rules['total']},
   'full_game_command_audit':{'status':'audit_complete','report':'evidence/refactor/compatibility_audit.json','sha256':sha(ROOT/'evidence/refactor/compatibility_audit.json'),'full_game_compatibility':'not_complete'},
  },
  'upstream_lock_sha256':lock_sha,'source_manifest_sha256':sha(ROOT/'source_manifest.json'),
  'logged_probe_commands':len(all_commands),'emulator_state_or_memory_write_commands':0,
  'probe_source_sha256':sha(ROOT/'tools/gba_acceptance_probe.c'),
  'ordinary_sav_write_version':3,'ordinary_sav_legacy_v2_read':'pass in menu acceptance fixtures',
  'full_user_fidelity_acceptance':'not_complete',
  'not_run':['其它出身完整章节','所有配方、称号、技能和支线','锻造/制甲的完整实际制作流程','完整战斗事件/并行事件/移动路线等全游戏兼容','PC原RPG_RT逐规则对照','GBA实机和烧录卡'],
  'notes':['原LCF对白与数值表未改写；框架分层不等于全游戏已经兼容。',
   '原作进入洞窟后会禁用自由保存；主路线和恢复测试遵守原许可，在城镇保存。',
   '声音为原MIDI及原SoundFont预转换；不承诺与PC逐采样一致。',
   '历史失败、拒绝及未运行记录保留，不计入本版通过项。'],
 }
 dump(ROOT/'acceptance_receipt.json',report)
 target=out/report['artifact'];shutil.copyfile(rom,target);assert sha(target)==digest
 for name in ['README.txt','ARCHITECTURE.txt','CREDITS.txt','LICENSE','acceptance_receipt.json']:
  shutil.copyfile(ROOT/name,out/name)
 previews={
  '称号界面.png':'evidence/refactor/menus/01_title_choices.png',
  '队伍称号.png':'evidence/refactor/menus/05_status_with_title.png',
  '料理界面.png':'evidence/refactor/menus/05_cooking_ingredients.png',
  '调和界面.png':'evidence/refactor/menus/03_alchemy_choices.png',
  '章节结束.png':'evidence/chapter_progress/19_returned_to_town.png',
 }
 for name,path in previews.items():shutil.copyfile(ROOT/path,out/name)
 play_zip=out/'废都物语_GBA_首章试玩_v0.2.zip'
 with zipfile.ZipFile(play_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in [target]+[out/n for n in ['README.txt','ARCHITECTURE.txt','CREDITS.txt','LICENSE','acceptance_receipt.json',*previews]]:
   z.write(p,'废都物语_GBA首章试玩_v0.2/'+p.name)
 project_zip=out/'废都物语_GBA_兼容框架工程_v0.2.zip';files=set()
 for directory in ['source','runtime','platform','tools','third_party','research','evidence']:
  for p in (ROOT/directory).rglob('*'):
   if not p.is_file() or '__pycache__'in p.parts or 'oracle'in p.parts:continue
   files.add(p)
 for name in ['README.txt','ARCHITECTURE.txt','CREDITS.txt','LICENSE','原包说明.txt','移植约定.json','acceptance_receipt.json','source_manifest.json']:
  files.add(ROOT/name)
 for name in ['assets.c','assets.h','asset_manifest.json','audio.bin','audio_manifest.json','original_lcf.bin','source_menu_labels.c','source_menu_manifest.json','build_receipt.json']:
  files.add(ROOT/'build'/name)
 files.update((ROOT/'build/original').glob('*'))
 files.update((ROOT/'build/audio_cache').glob('*.adpcm'))
 for name in ['legacy_checkpoint_v2.sav','legacy_reentered_cave_v2.sav']:files.add(ROOT/'history'/name)
 with zipfile.ZipFile(project_zip,'w',zipfile.ZIP_DEFLATED,compresslevel=6)as z:
  for p in sorted(files):z.write(p,'废都物语_GBA章节样版/'+str(p.relative_to(ROOT)))
 for p in [play_zip,project_zip]:
  with zipfile.ZipFile(p)as z:assert z.testzip()is None
 download=Path('/mnt/c/Users/APP/Downloads/废都物语_GBA兼容框架_v0.2_20261021');download.mkdir(exist_ok=True)
 for p in [target,play_zip,project_zip]:shutil.copyfile(p,download/p.name);assert sha(download/p.name)==sha(p)
 receipt={'version':VERSION,'rom':{'file':target.name,'bytes':target.stat().st_size,'sha256':digest},'packages':[{'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)}for p in [play_zip,project_zip]],'download_directory':str(download),'zip_crc_check':'pass','offline_source_zip_rebuild':'pending separate validation'}
 dump(out/'交付校验.json',receipt);shutil.copyfile(out/'交付校验.json',download/'交付校验.json')
 print(json.dumps(receipt,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
