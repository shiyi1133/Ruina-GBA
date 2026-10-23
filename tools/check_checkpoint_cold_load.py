"""Cold-load the ordinary SAV produced by the current natural first-CP run."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator
from save_observation import save_payload,check_load

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest();progress=ROOT/'evidence/chapter_progress/progress.json';r=json.loads(progress.read_text());assert r['status']=='pass'and r['chapter_complete']and r['rom_sha256']==digest
 names=[s['name']for s in r['milestones']]
 expected=['01_cave_entered','05_nell_recruited','06_laban_recruited','18_first_checkpoint_cleared','19_returned_to_town'];assert [names.index(n)for n in expected]==sorted(names.index(n)for n in expected)
 save=ROOT/'evidence/chapter_progress/after_checkpoint_town.sav';version,payload=save_payload(save.read_bytes());assert version==5
 out=ROOT/'evidence/optimization_20261022/checkpoint_cold_load'/digest[:12];out.mkdir(parents=True,exist_ok=True);e=Emulator(save)
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(180);assert e.debug()[15]==4 and e.debug()[9]==3
  state=check_load(e,payload);e.frames(2);e.shot(out/'after_checkpoint_cold_load.png');g=e.memory(e.symbols['game'],39704)
  values={'map':struct.unpack_from('<i',g,29768)[0],'story_phase':struct.unpack_from('<i',g,8+41*4)[0],'SP':struct.unpack_from('<i',g,8+26*4)[0],'original_title_certificates':g[3133+201],'CP_flag_114':bool(g[2012+114]),'gold':struct.unpack_from('<i',g,29744)[0],'party':list(struct.unpack_from('<3i',g,29748))}
  assert values['story_phase']==15 and values['CP_flag_114']and values['original_title_certificates']==1 and values['party']==[1,6,7]
  result={'status':'pass','production_rom_sha256':digest,'natural_run_report':'evidence/chapter_progress/progress.json','natural_run_report_sha256':hashlib.sha256(progress.read_bytes()).hexdigest(),'genuine_SAV_sha256':hashlib.sha256(save.read_bytes()).hexdigest(),'load_observations':state,'progress':values,'kind':'production ROM, fresh emulator process, ordinary SAV from actual current knight opening-to-first-CP gameplay, actual buttons and read-only observations','full_game':'not_run','hardware':'not_run','commands':e.log};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
