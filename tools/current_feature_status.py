"""Record current, historical, rejected and unrun evidence separately."""
import hashlib,json
from project_env import ROOT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(name):return json.loads((ROOT/name).read_text())
def main():
 rom=ROOT/'build/废都物语_GBA_开篇开发验证版.gba';digest=sha(rom)
 build=read('build/build_receipt.json');assert build['sha256']==digest
 paths={
  'delivered_demo_opening_walk_and_victory':'evidence/demo_20261021/result.json',
  'incremental_map_pixel_equivalence':'evidence/performance/map_dirty/result.json',
  'opening_checkpoint_and_return':'evidence/chapter_progress/progress.json',
  'ordinary_sav_cold_load':'evidence/save_cold_load/result.json',
  'source_menu_examples_and_legacy_sav':'evidence/refactor/menus/result.json',
  'defeat_new_game_and_bad_sav':'evidence/recovery/result.json',
  'opening_PCM_output':'evidence/audio/result.json',
  'opening_PCM_loop':'evidence/audio/loop_result.json',
  'walk_handbook_world_map_weapon_armor':'evidence/full_features/interfaces/result.json',
  'battle_enemy_capacity':'evidence/mechanisms/battle_capacity/result.json',
 }
 paths.update({f'origin_{i}_first_battle':f'evidence/first_battle_origin_{i}/result.json'for i in range(1,5)})
 if (ROOT/'evidence/naming_cut/latest_attempt.json').exists():
  paths['actual_naming_to_cave_black_cuts']=read('evidence/naming_cut/latest_attempt.json')['report']
 if (ROOT/'evidence/hardware_scroll/navigation/latest_attempt.json').exists():
  paths['actual_navigation_markers_and_scroll']=read('evidence/hardware_scroll/navigation/latest_attempt.json')['report']
 if (ROOT/'evidence/cursor_flash/latest_attempt.json').exists():
  paths['cursor_every_LCD_frame_continuity']=read('evidence/cursor_flash/latest_attempt.json')['report']
 paths['hardware_scroll_cache_pixel_equivalence']='evidence/hardware_scroll/cache/result.json'
 paths['native_map_pixel_crops']='evidence/hardware_scroll/native_crop/result.json'
 for name,path in [('historical_full_SoundFont_MIDI_experiment','evidence/full_features/native_audio/latest_attempt.json'),('reduced_animation','evidence/full_features/presentation/latest_attempt.json'),('original_portraits','evidence/full_features/portraits/latest_attempt.json'),('uniform_picture_alpha','evidence/full_features/uniform_alpha/latest_attempt.json'),('phase_demo_actual_buttons_and_cold_load','evidence/phase_demo_20261021/latest_attempt.json')]:
  if (ROOT/path).exists():paths[name]=read(path)['report']
 for name,path in [('all_panorama_crops','panorama_matrix'),('all_native_characters','characters'),('changing_actor_palettes','actor_palette_churn'),('all_portraits_plus_music_and_SFX','portrait_matrix'),('status_browsing','status_ui'),('menu_stack_observation','stack'),('dense_actors_HUD_and_music','dense_actor_transition'),('natural_first_CP_cold_load','checkpoint_cold_load'),('extended_gameplay','extended_acceptance'),('music_room_one_shot_replay','music_room_replay')]:
  pointer=f'evidence/optimization_20261022/{path}/'+('latest_stress_attempt.json'if path=='portrait_matrix'else'latest_attempt.json')
  if(ROOT/pointer).exists():paths[name]=read(pointer)['report']
 for name,pointer in [('all_MIDI_peak_excerpts','evidence/optimization_20261022/music/gba_matrix/latest_attempt.json'),('original_music_pitch_uses','evidence/optimization_20261022/music/gba_matrix/latest_pitch_attempt.json'),('complete_simplified_GBA_music','evidence/optimization_20261022/music/complete_GBA/latest_attempt.json'),('music_room_UI','evidence/optimization_20261022/music_room/latest_attempt.json')]:
  if(ROOT/pointer).exists():paths[name]=read(pointer)['report']
 def evidence(path,host=False):
  p=ROOT/path
  if not p.exists():return {'status':'not_run','report':path}
  r=read(path);original=r.get('status',r.get('result','pass'if r.get('chapter_complete')else 'unknown'))
  d=next((r[k]for k in ('production_rom_sha256','rom_sha256','release_rom_sha256')if k in r),None)
  if not d and r.get('records'):
   digests={v.get('production_rom_sha256')for v in r['records']};d=next(iter(digests))if len(digests)==1 else None
  bound=r.get('production_sources_sha256',r.get('sources_sha256',r.get('sources',r.get('source_sha256',{}))));bound=bound if isinstance(bound,dict)else {}
  if path.endswith('lcf_cache.json'):bound={'runtime/rm2k/lcf.c':r['source_sha256']}
  if '/borrowed_commands/'in path:bound={'runtime/rm2k/lcf.c':r['source_sha256'],'build/borrowed_commands.c':r['linked_views_sha256'],'build/original_lcf.bin':r['original_pack_sha256']}
  if path.endswith('complete_score_census.json'):bound={'runtime/rm2k/light_midi.c':r['source_sha256'],'runtime/rm2k/native_midi.h':r['header_sha256'],'build/native_music/native_soundfont.bin':r['bank_sha256']}
  changed=[n for n,h in bound.items()if not (ROOT/n).exists()or sha(ROOT/n)!=h]
  if 'native_source_sha256'in r and r['native_source_sha256']!=sha(ROOT/'runtime/rm2k/rm2k_rules.c'):changed.append('runtime/rm2k/rm2k_rules.c')
  passed=original=='pass'or original=='opening_to_cave_reached'
  status=(('pass_current_sources'if not changed else 'pass_historical')if host and bound else 'pass_unbound_sources'if host else 'pass_current_ROM'if d==digest else 'pass_historical')if passed else str(original)
  return {'status':status,'reported_status':original,'report':path,'sha256':sha(p),'evidence_rom_sha256':d,'current_ROM':d==digest if d else None,'changed_sources':changed,'kind':'host fixture; not natural GBA gameplay'if host else 'GBA emulator report; scope remains that report'}
 gameplay={name:evidence(path)for name,path in paths.items()}
 host_paths={
  'original_data_reader':'evidence/native_reader_checks.json',
  'immutable_LCF_cache_parity':'evidence/performance/lcf_cache.json',
  'baseline_rules':'evidence/refactor/rule_parity.json',
  'shared_rules':'evidence/mechanisms/shared_rule_parity.json',
  'original_event_and_full_feature_fixtures':'evidence/mechanisms/host_event_integration.json',
  'predecoded_ROM_event_fixtures':'evidence/mechanisms/host_event_integration_predecoded.json',
  'live_page_condition_transport':'evidence/optimization_20261022/page_transport/result.json',
  'borrowed_immutable_operands':'evidence/optimization_20261022/borrowed_commands/result.json',
  'exact_audio_IRQ_arithmetic':'evidence/optimization_20261022/audio_irq/result.json',
  'complete_simplified_scores_and_loops':'evidence/optimization_20261022/music/complete_score_census.json',
  'image_bounds_and_storage':'evidence/full_features/storage_images_host.json',
  'actual_original_resource_requirements':'evidence/full_features/original_requirements.json',
 }
 host={name:evidence(path,True)for name,path in host_paths.items()}
 audit=read('evidence/refactor/compatibility_audit.json')
 sources=[]
 for directory in ['source','runtime','platform','tools','tests']:
  sources += [{'path':str(p.relative_to(ROOT)),'sha256':sha(p)}for p in sorted((ROOT/directory).rglob('*'))if p.is_file()and '__pycache__'not in p.parts]
 final_pointer='evidence/optimization_20261022/final_validation/latest_attempt.json';final=read(read(final_pointer)['report'])if(ROOT/final_pointer).exists()else{}
 report={'date':'2026-10-22','status':'optimized stage; full natural campaign and PC parity not established','active_phase':2,'work_order':['补齐原作所需特性并做执行抽查','整体优化运行效率与图片质量'],'full_game_port':False,'all_original_features_accepted':False,'rom_sha256':digest,'rom_bytes':rom.stat().st_size,'within_GBA_32MiB':rom.stat().st_size<=33554432,'released_v0_2_preserved':True,'delivered_demo_preserved':True,'gameplay_checks':gameplay,'host_checks':host,'current_regression':{'report':final_pointer,'status':final.get('status','not_run')if final.get('rom_sha256')==digest else'not_current_ROM','completed':final.get('completed',0)},'original_command_inventory':{'count':audit['commands_observed'],'report':'evidence/refactor/compatibility_audit.json','case_presence_is_not_acceptance':True},'remaining_functional_gaps':audit['functional_gaps'],'music_policy':'Both modes use simplified original-score timbres. Gameplay is coarser mono; music room is finer stereo. No original-SoundFont split carts.','save_format':{'write_version':5,'reads_released_versions':[2,3,4,5],'game_bytes':39704,'SRAM_bytes':32768,'encoding':'exact packed state, checksum, refuse overflow before writing existing save'},'animation_policy':'direct black cuts, no fades; see 动画简化说明.txt','full_natural_playthrough':'user acceptance, not required from developer by user instruction','hardware':'not_run','original_RPG_RT_executable_comparison':'not_run','performance_phase':'spot checks and controlled benchmarks separately bound to this ROM; not all-scene PC parity','sources':sources}
 path=ROOT/'evidence/mechanisms/functional_status.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in report.items()if k not in ['sources','remaining_functional_gaps','host_checks','gameplay_checks']},ensure_ascii=False,indent=2))
 print(json.dumps({name:r['status']for name,r in gameplay.items()},ensure_ascii=False))
if __name__=='__main__':main()
