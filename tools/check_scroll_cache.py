"""Compare hardware-scrolled cache with rebuilding the same complete view."""
import hashlib,json,struct
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture

def main():
 out=ROOT/'evidence/hardware_scroll/cache';out.mkdir(parents=True,exist_ok=True)
 screenshots={};records=[]
 for name,source in [('full','tests/map_scroll_reference_gba.c'),('cache','tests/map_scroll_gba.c')]:
  rom,elf,digest=fixture(source,'scroll_'+name);folder=out/name;folder.mkdir(exist_ok=True)
  e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf);rows=[];screens=[]
  try:
   for stage in range(1,16):
    for _ in range(1500):
     if e.debug()[14]==stage:break
     e.frames(1)
    else:raise AssertionError(('stage timeout',name,stage,e.debug()))
    e.frames(2);path=folder/f'{stage:02}.png';e.shot(path);screens.append(np.asarray(Image.open(path).convert('RGB')))
    metric=list(struct.unpack('<8I',e.memory(e.symbols['map_video_metrics'],32)))
    rows.append({'stage':stage,'BG_tile_uploads':metric[0],'BG_bytes_uploaded':metric[1],
                 'screen_presentations':metric[2],'actor_uploads':metric[4],
                 'native_commit_metrics':list(struct.unpack('<3I',e.memory(e.symbols['video_native_commit_metrics'],12))),'display_control':struct.unpack('<H',e.memory(0x04000000,2))[0]})
    e.frames(2,1);e.frames(2)
   screenshots[name]=screens;records.append({'variant':name,'rows':rows,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'production_rom_sha256':digest,'commands':e.log})
  finally:e.close()
 differences=[int(np.any(a!=b,axis=2).sum())for a,b in zip(screenshots['full'],screenshots['cache'])]
 rows=records[1]['rows'];deltas=[b['BG_tile_uploads']-a['BG_tile_uploads']for a,b in zip(rows,rows[1:])]
 checks={'all_native_commits_within_VBlank':all(r['native_commit_metrics'][0]==0 for rec in records for r in rec['rows']),'all_pixels_equal_full_rebuild':not any(differences),
         'horizontal_scroll_uploads_at_most_new_columns':0<=deltas[1]<=40 and 0<=deltas[2]<=40,
         'vertical_scroll_uploads_at_most_new_rows':0<=deltas[3]<=60,
         'returning_to_resident_columns_needs_no_pixel_upload':deltas[2]==0,
         'turning_does_not_upload_background':deltas[7]==0,
         'moving_HUD_does_not_upload_background':deltas[8]==0,
         'menu_preserves_all_background_tiles':deltas[10]==0,
         'menu_is_independent_BG_layer':(rows[10]['display_control']&0x307)==0x300,
         'menu_return_disables_only_overlay':(rows[11]['display_control']&0x307)==0x100,
         'map_uses_tiled_BG_mode':all((r['display_control']&7)==0 for r in rows if r['stage']!=11)}
 result={'status':'pass'if all(checks.values())else'fail','checks':checks,'different_pixels':differences,'BG_upload_deltas':deltas,
         'kind':'controlled real GBA cartridges; same genuine ordinary save, current compositor full viewport rebuild versus ring cache',
         'production_rom_sha256':records[0]['production_rom_sha256'],'records':records,'natural_gameplay':'separate test','hardware':'not_run'}
 (out/('result_'+result['production_rom_sha256'][:12]+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='records'},ensure_ascii=False,indent=2),flush=True)
 assert result['status']=='pass',checks

if __name__=='__main__':main()
