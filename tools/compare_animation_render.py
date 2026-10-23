"""Compare identical real LCD animation frames and hardware timer costs."""
import json,statistics,hashlib
from pathlib import Path
import numpy as np
from PIL import Image
from project_env import ROOT

def main():
 out=ROOT/'evidence/animation_optimization_20261023';baseline=json.loads((out/'baseline/gallery.json').read_text());old=Path(json.loads((out/'baseline/gallery_location.json').read_text())['directory']);ref=Path(json.loads((ROOT/'evidence/battle_animations_20261023/gallery_latest.json').read_text())['report']);current=json.loads(ref.read_text());assert current['production_ROM_sha256']==hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest(),'Current benchmark has not completed for this build';new=ref.parent;before={r['id']:r for r in baseline['rows']};rows=[]
 for r in current['rows']:
  aid=r['id'];a=before[aid];assert a['source_frame']==r['source_frame'];p='animation_%03d.png'%aid;exact=np.array_equal(np.asarray(Image.open(old/p)),np.asarray(Image.open(new/p)));assert exact,('LCD differs',aid)
  b=a['trace'][9]*1024/16777216*1000;c=r['trace'][9]*1024/16777216*1000
  rows.append({'animation':aid,'baseline_ms':b,'candidate_ms':c,'speedup':b/c if c else None,'LCD_pixels_identical':exact})
 summary={'status':'pass','baseline_ROM':baseline['production_ROM_sha256'],'candidate_ROM':current['production_ROM_sha256'],'frames_compared':len(rows),'LCD_pixels_identical':True,'baseline_mean_ms':statistics.mean(r['baseline_ms']for r in rows),'candidate_mean_ms':statistics.mean(r['candidate_ms']for r in rows),'baseline_median_ms':statistics.median(r['baseline_ms']for r in rows),'candidate_median_ms':statistics.median(r['candidate_ms']for r in rows),'baseline_worst_ms':max(r['baseline_ms']for r in rows),'candidate_worst_ms':max(r['candidate_ms']for r in rows),'total_render_speedup':sum(r['baseline_ms']for r in rows)/sum(r['candidate_ms']for r in rows),'scope':'Same 213 selected original animation frames, unchanged foreground/background, exact LCD comparison. Timer2 on actual emulated GBA hardware; includes draw and present, excludes user key timing and initialization. Not average gameplay FPS.','rows':rows}
 (out/('comparison_'+current['production_ROM_sha256'][:12]+'.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in summary.items()if k!='rows'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
