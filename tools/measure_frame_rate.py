"""Count actual LCD page changes and engine updates using read-only probes.
An idle unchanged menu does not redraw 60 times per second; that is not a
performance failure. Movement/map refresh and wait-loop updates are separate.
"""
import hashlib,json,struct,sys
from drive_opening import ROOT,Emulator

FPS=16777216/280896
def u32(e,address):return struct.unpack('<I',e.memory(address,4))[0]
def scene(e,label,frames,keys):
 page=e.symbols['page'];last=u32(e,page);changes=0
 map_counter=e.symbols.get('map_video_metrics');map_start=u32(e,map_counter+8)if map_counter else 0
 bitmap_counter=e.symbols.get('video_metrics');bitmap_start=u32(e,bitmap_counter+16)if bitmap_counter else 0
 tile_start=u32(e,map_counter)if map_counter else 0
 updates=u32(e,e.symbols['parallel_trace']+16)
 audio=u32(e,e.symbols['audio_debug']+12);positions=[]
 for i in range(frames):
  e.frames(1,keys(i));value=u32(e,page)
  changes+=value!=last;last=value
  if i%30==0:positions.append(struct.unpack('<3i',e.memory(e.symbols['game']+29768,12)))
 seconds=frames/FPS;actual=u32(e,e.symbols['parallel_trace']+16)-updates
 map_updates=u32(e,map_counter+8)-map_start if map_counter else 0;tile_uploads=u32(e,map_counter)-tile_start if map_counter else 0
 bitmap_updates=u32(e,bitmap_counter+16)-bitmap_start if bitmap_counter else 0
 return {'scene':label,'hardware_seconds':seconds,'completed_display_page_changes':changes,'bitmap_or_UI_presentations':bitmap_updates,'hardware_BG_presentations':map_updates,'BG_tiles_uploaded':tile_uploads,'display_updates_per_second':(max(changes,bitmap_updates)+map_updates)/seconds,'engine_updates_per_second':actual/seconds,'position_samples':positions,'final_ui_mode':e.debug()[15],'audio_source_frames_advanced':u32(e,e.symbols['audio_debug']+12)-audio}

def main():
 variants=[('delivered_demo',ROOT/'history/pre_native_playback_20261021'),('development',ROOT/'build')]
 if '--cursor-fix'in sys.argv:variants=[('baseline_v0.5',ROOT/'history/pre_cursor_fix_20261021'),('development',ROOT/'build')]
 if '--baseline-v051'in sys.argv:variants=[('baseline_v0.5.1',ROOT/'history/quality_performance_20261022/baseline/build'),('development',ROOT/'build')]
 if '--current-only'in sys.argv:variants=[('development',ROOT/'build')]
 reports=[]
 for name,directory in variants:
  rom=directory/'废都物语_GBA_开篇开发验证版.gba';elf=directory/'ruina_opening_dev.elf'
  e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf)
  try:
   e.frames(60);e.key(1);e.key(128);e.key(1);e.frames(120)
   assert e.debug()[15]==4,e.debug()
   rows=[scene(e,'cave idle',180,lambda i:0)]
   rows.append(scene(e,'cave walking up/down',300,lambda i:64 if (i//30)%2==0 else 128))
   rows.append(scene(e,'cave point selector redraw',180,lambda i:256 if i%30<3 else 0))
   if 'map_video_metrics'in e.symbols:rows.append(scene(e,'cave camera scroll',300,lambda i:256|(64 if (i//30)%2==0 else 128)))
   e.key(8);e.frames(60)
   rows.append(scene(e,'menu idle',180,lambda i:0))
   reports.append({'version':name,'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'kind':'ordinary save load, actual buttons, read-only page/engine observations','scenes':rows,'commands':e.log})
  finally:e.close()
 out=ROOT/'evidence/performance';out.mkdir(exist_ok=True)
 result={'status':'measured','hardware_refresh_Hz':FPS,'method':'Bitmap/UI completion counter (or legacy page flips, whichever is larger) plus hardware BG presentation counters, sampled once per hardware frame; engine updates observed independently. BG scrolling and OBJ blinking do not flip bitmap pages. Static scenes intentionally do not redraw. Not physical hardware.','reports':reports}
 (out/'frame_rate_20261021.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 if '--cursor-fix'in sys.argv:(out/('cursor_fix_'+reports[-1]['rom_sha256'][:12]+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({'hardware_refresh_Hz':FPS,'reports':[{k:v for k,v in r.items()if k!='commands'}for r in reports]},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
