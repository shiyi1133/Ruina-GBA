"""Real title-menu buttons, playback/pause/quality controls, six PCM BGMs."""
import hashlib,json,struct
from project_env import ROOT
from drive_opening import Emulator

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/music_room'/digest[:12];out.mkdir(parents=True,exist_ok=True);tracks=[t for t in json.loads((ROOT/'build/audio_manifest.json').read_text())['tracks']if t['kind']=='music'];e=Emulator();checks={};rows=[]
 def audio():return struct.unpack('<8I',e.memory(e.symbols['audio_debug'],32))
 def paused():return struct.unpack('<i',e.memory(e.symbols['music_paused'],4))[0]
 def position():return audio()[3]
 def toggle_paused_quality(label):
  if not paused():e.key(1)
  before=position();quality=e.debug()[19];e.frames(60);assert position()==before and paused();e.key(8);assert paused()and position()==before,(label,before,position(),e.debug());assert e.debug()[19]!=quality;e.shot(out/(label+'_paused_quality.png'));rows.append({'name':label,'paused_position_before':before,'after_quality_switch':position(),'remains_paused':True});e.key(1);e.frames(60);assert position()!=before
 try:
  e.frames(30);e.key(1)
  for _ in range(3):e.key(128)
  e.key(1);assert e.debug()[15]==18 and e.debug()[17]==105,e.debug();e.shot(out/'music_room_open.png');checks['105_music_entries_on_title_menu']=True
  e.key(1);e.frames(60);assert audio()[1]==tracks[0]['id']and position()>0;toggle_paused_quality('first_MIDI');checks['MIDI_pause_resume_and_quality_seek']=True
  e.key(256);assert e.debug()[16]==1 and audio()[1]==tracks[1]['id'];e.key(512);assert e.debug()[16]==0 and audio()[1]==tracks[0]['id'];checks['shoulder_buttons_change_and_play_tracks']=True
  e.key(64);assert e.debug()[16]==104;checks['selection_wraps_up_to_last_track']=True
  for index in range(104,98,-1):
   assert e.debug()[16]==index,e.debug();e.key(1);e.frames(60);track=tracks[index];assert track['source'].lower().endswith('.wav')and audio()[1]==track['id'];toggle_paused_quality('WAV_%d'%track['id']);e.key(64)
  checks['all_six_WAV_quality_toggles_keep_position_and_pause']=len(rows)==7
  e.key(2);e.frames(90);assert e.debug()[15]!=18 and audio()[1]==0;assert struct.unpack('<i',e.memory(e.symbols['music_quality'],4))[0]==0;assert struct.unpack('<i',e.memory(e.symbols['engine_clock_paused'],4))[0]==0;checks['exit_restores_normal_quality_clock_and_previous_silence']=True
  result={'status':'pass','kind':'actual production ROM title-menu inputs, no memory writes or save states','production_rom_sha256':digest,'checks':checks,'seek_observations':rows,'physical_hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
 except Exception as err:
  e.shot(out/'failed.png');(out/'failed_attempt.json').write_text(json.dumps({'status':'fail','error':str(err),'debug':e.debug(),'audio':audio(),'commands':e.log},ensure_ascii=False,indent=2));raise
 finally:e.close()
if __name__=='__main__':main()
