"""Fetch reviewed upstream references at immutable commits, with file hashes.

These sources are references for the freestanding GBA adapter, not a claim that
the desktop EasyRPG Player is linked into or runnable on the GBA.
"""
import concurrent.futures,hashlib,json,urllib.request,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCES={
 'Player':('78328fa29f465315291e161130e6682f69410370','0.8.1.1',[
  'COPYING','README.md','src/player.h','src/game_variables.cpp','src/game_variables.h','src/algo.cpp','src/algo.h','src/game_actor.cpp',
  'src/game_interpreter.cpp','src/game_interpreter_map.cpp','src/game_interpreter_battle.cpp',
  'src/game_battlealgorithm.cpp','src/enemyai.cpp','src/autobattle.cpp',
  'src/game_battle.cpp','src/game_battle.h','src/scene_battle_rpg2k.cpp','src/scene_battle_rpg2k.h',
  'src/game_map.cpp','src/game_map.h','src/game_party.cpp','src/game_party.h','src/game_event.cpp','src/game_commonevent.cpp',
  'src/map_data.h','src/game_interpreter_control_variables.cpp','src/game_interpreter_control_variables.h','src/audio_generic.cpp','src/audio_generic_midiout.cpp','src/audio_decoder_midi.cpp','src/midisequencer.cpp','src/game_enemy.cpp','src/scene_battle.cpp','src/game_interpreter_shared.cpp','src/game_interpreter_shared.h','src/game_character.cpp','src/game_character.h','src/game_player.cpp','src/game_battler.cpp','src/game_screen.cpp','src/battle_animation.cpp','src/battle_animation.h','src/state.cpp','src/state.h','src/attribute.cpp','src/game_system.h','src/game_system.cpp','src/tilemap.cpp','src/tilemap.h','src/tilemap_layer.cpp','src/tilemap_layer.h']),
 'liblcf':('92c4450a1bc1acb58bd02bbb99b57e5036919cdf','0.8.1',[
  'COPYING','README.md','src/generated/lcf/rpg/eventcommand.h',
  'src/generated/lcf/rpg/actor.h','src/generated/lcf/rpg/skill.h',
  'src/generated/lcf/rpg/item.h','src/generated/lcf/rpg/eventpagecondition.h',
  'src/generated/lcf/rpg/enemyaction.h','src/generated/lcf/ldb/chunks.h',
  'src/generated/lcf/lmu/chunks.h','src/generated/lcf/rpg/trooppagecondition.h','src/generated/lcf/rpg/trooppage.h','src/generated/lcf/rpg/troopmember.h','src/generated/lcf/rpg/map.h','src/generated/lcf/rpg/movecommand.h','src/generated/lcf/rpg/eventpage.h','src/generated/lcf/rpg/chipset.h','src/generated/lcf/rpg/terrain.h','src/generated/lcf/rpg/system.h','src/generated/lcf/rpg/state.h','src/generated/lcf/rpg/music.h','src/generated/lcf/rpg/savesystem.h'])}
LOCK=ROOT/'third_party/sources.lock.json'
KNOWN={(f['project'],f['path']):f for f in json.loads(LOCK.read_text())['files']} if LOCK.exists() else {}
def fetch(task):
 name,commit,path=task
 url=f'https://raw.githubusercontent.com/EasyRPG/{name}/{commit}/{path}'
 target=ROOT/'third_party'/name/path
 known=KNOWN.get((name,path))
 if known and target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==known['sha256']:return known
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for attempt in range(3):
  try:
   with opener.open(urllib.request.Request(url,headers={'User-Agent':'Ruina-GBA-source-refactor'}),timeout=12)as response:data=response.read(2*1024*1024)
   break
  except Exception:
   if attempt==2:raise
   time.sleep(1)
 target=ROOT/'third_party'/name/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
 return {'project':name,'path':path,'url':url,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def main():
 tasks=[(name,commit,path)for name,(commit,tag,paths)in SOURCES.items()for path in paths]
 with concurrent.futures.ThreadPoolExecutor(max_workers=6)as pool:files=list(pool.map(fetch,tasks))
 manifest={'kind':'pinned reference source, adapted selectively for native GBA',
  'projects':{name:{'repository':f'https://github.com/EasyRPG/{name}','commit':commit,'tag':tag}for name,(commit,tag,paths)in SOURCES.items()},'files':files}
 (ROOT/'third_party/sources.lock.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 print(json.dumps({'status':'downloaded','files':len(files),'bytes':sum(f['bytes']for f in files)}))
if __name__=='__main__':main()
