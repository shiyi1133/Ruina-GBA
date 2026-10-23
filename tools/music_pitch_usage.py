"""Audit actual BGM pitch requests from all original maps/commons/troops/system."""
import collections,json
from project_env import ROOT
from inspect_lcf import Reader,array,commands,data_root,fields,integer,filename

def collect():
 uses=[]
 def add(name,pitch,location):
  if name and not name.startswith('('):uses.append({'name':name,'pitch':pitch,'source':location})
 def stream(blob,where):
  for i,c in enumerate(commands(blob)):
   if c['code']==11510:add(c['file'],c['params'][2],where+'/command'+str(i))
   if c['code']==10660:add(c['file'],c['params'][3],where+'/system_music/command'+str(i))
 for path in sorted((ROOT/'build/original').glob('*.lmu')):
  root=data_root(path.read_bytes())[1]
  for eid,e in array(root.get(81,b'')):
   for pid,p in array(e.get(5,b'')):stream(p.get(52,b''),f'{path.name}/event{eid}/page{pid}')
 db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1]
 for cid,c in array(db.get(25,b'')):stream(c.get(22,b''),f'common{cid}')
 for tid,t in array(db.get(15,b'')):
  for pid,p in array(t.get(11,b'')):stream(p.get(12,b''),f'troop{tid}/page{pid}')
 system=fields(db[22])
 for i in range(32,40):
  m=fields(system.get(i,b''));add(filename(m.get(1,b'')),integer(m.get(4,b''),100),f'system_music{i-32}')
 raw=(ROOT/'build/original/RPG_RT.lmt').read_bytes();r=Reader(raw);r.string()
 for mid,m in array(raw[r.at:]):
  if integer(m.get(11,b''))==2:
   music=fields(m.get(12,b''));add(filename(music.get(1,b'')),integer(music.get(4,b''),100),f'map_tree{mid}')
 cases=collections.defaultdict(list)
 for row in uses:cases[row['name'],row['pitch']].append(row['source'])
 result={'music_commands_and_defaults':len(uses),'source_pitch_counts':dict(collections.Counter(r['pitch']for r in uses)),'distinct_name_pitch_pairs':len(cases),'cases':[{'name':name,'pitch':pitch,'source_uses':locations}for(name,pitch),locations in sorted(cases.items())]}
 return result
if __name__=='__main__':
 result=collect();out=ROOT/'evidence/optimization_20261022/music/original_pitch_usage.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='cases'},ensure_ascii=False,indent=2))
