"""Compare retained VRAM pixels with complete rebuilds across map/cache changes."""
import hashlib,json,struct
import numpy as np
from PIL import Image
from gba_fixture import fixture
from drive_opening import ROOT,Emulator

def main():
 screenshots={};records=[];production=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/residency'/production[:12];out.mkdir(parents=True,exist_ok=True)
 for variant,source in [('full','tests/map_residency_reference_gba.c'),('cache','tests/map_residency_gba.c')]:
  rom,elf,digest=fixture(source,'residency_'+variant);e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf);rows=[];screens=[];folder=out/variant;folder.mkdir(exist_ok=True)
  try:
   for stage in range(1,26):
    for _ in range(3000):
     if e.debug()[14]==stage:break
     e.frames(1)
    else:raise AssertionError((variant,stage,e.debug()))
    e.frames(2);path=folder/f'{stage:02}.png';e.shot(path);screens.append(np.asarray(Image.open(path).convert('RGB')));rows.append({'stage':stage,'map_video_metrics':struct.unpack('<8I',e.memory(e.symbols['map_video_metrics'],32)),'native_commit_metrics':struct.unpack('<3I',e.memory(e.symbols['video_native_commit_metrics'],12)),'debug':e.debug()});e.frames(2,1);e.frames(2)
   screenshots[variant]=screens;records.append({'variant':variant,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'rows':rows})
  finally:e.close()
 differences=[int(np.any(a!=b,axis=2).sum())for a,b in zip(screenshots['full'],screenshots['cache'])];cached=records[1]['rows'];checks={'all_native_commits_within_VBlank':all(r['native_commit_metrics'][0]==0 for rec in records for r in rec['rows']),'all_pixels_match_complete_rebuild':not any(differences),'resident_regions_reused':cached[-1]['map_video_metrics'][3]>0,'texture_and_screen_map_wraps_checked':len(differences)==25,'HUD_reclassification_and_offscreen_erase_checked':not any(differences[11:19]),'map_transition_checked':differences[-1]==0}
 result={'status':'pass'if all(checks.values())else'fail','kind':'controlled actual GBA cartridges; original save; independent full-view rebuild versus retained VRAM pixels','production_rom_sha256':production,'checks':checks,'different_pixels':differences,'records':records,'physical_hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':result['status'],'report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='records'},ensure_ascii=False,indent=2));assert result['status']=='pass'

if __name__=='__main__':main()
