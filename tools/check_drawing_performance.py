"""Compare full repaint with incremental map updates on the same core."""
import hashlib,json,struct
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture

def main():
 out=ROOT/'evidence/performance/drawing';out.mkdir(parents=True,exist_ok=True)
 old='history/pre_fused_drawing_20261021/'
 rows=[];screens=[]
 for name,overrides in [('before',{'video':old+'video.c','image':old+'image.c','world':'history/pre_dirty_map_20261021/world.c','map_rules':'history/pre_dirty_map_20261021/map_rules.c'}),('after',None)]:
  rom,elf,digest=fixture('tests/drawing_performance_gba.c','drawing_'+name,overrides)
  e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf)
  try:
   # A redraw can be slow; wait until at least one whole frame was presented.
   for _ in range(300):
    e.frames(30)
    if e.debug()[14]:break
   else:raise AssertionError(('first frame never completed',e.debug()))
   before=e.debug()[14];e.frames(600);after=e.debug()[14]
   p=out/(name+'.png');e.shot(p);screens.append(np.asarray(Image.open(p).convert('RGB')))
   seconds=600*280896/16777216
   metrics={n:list(struct.unpack('<8I',e.memory(e.symbols[n],32)))for n in ('world_metrics','video_metrics')if n in e.symbols}
   rows.append({'variant':name,'metrics':metrics,'completed_map_updates':after-before,'seconds':seconds,'map_updates_per_second':(after-before)/seconds,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'production_rom_sha256':digest,'commands':e.log})
  finally:e.close()
 # Screenshots during repeated flipping may straddle pages; identical input
 # pixels are checked independently by the host renderer fixture.
 result={'status':'measured','kind':'controlled facing changes on genuine ordinary-save scene; isolated cartridges; full-paint reference and incremental renderer share current audio and parser','rows':rows,'not_a_full_game_FPS_benchmark':True,'screen_scanout_can_straddle_flips':True,'physical_hardware':'not_run'}
 (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps({'rows':[{k:v for k,v in r.items()if k!='commands'}for r in rows]},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
