"""Audit the original game's actual resources and optional engine forms.
This is static coverage; it does not claim a natural campaign playthrough.
"""
import collections,hashlib,json,struct
from inspect_lcf import ROOT,Reader,array,fields,integer,data_root

def h(data):
 n=2166136261
 for b in data:n=((n^b)*16777619)&0xffffffff
 return n
def rawcommands(data):
 r=Reader(data)
 while r.at<len(data):
  code=r.num();r.num();name=r.string();p=[r.num()for _ in range(r.num())];yield code,name,p

def main():
 manifest=json.loads((ROOT/'build/asset_manifest.json').read_text());resources={(r['kind'],r['hash'])for r in manifest['resources']}
 b=(ROOT/'build/audio.bin').read_bytes();audio={(struct.unpack_from('<I',b,8+i*28)[0],struct.unpack_from('<I',b,12+i*28)[0])for i in range(struct.unpack_from('<I',b,4)[0])}
 # Kind 2 is original MIDI played from a shared ROM SoundFont.
 audio|={(name,0)for name,kind in audio if kind==2}
 missing=[];unused_defaults=[];counts=collections.Counter();streams=[];move_types=collections.Counter();max_picture=0;max_cells=0;used_chipsets=set()
 def resource(kind,name,where):
  if not name:return
  counts['image references']+=1
  if (kind,h(name))not in resources:missing.append({'kind':kind,'name':name.hex(),'where':where})
 def sound(name,kind,where):
  if not name or name.startswith(b'('):return
  counts['audio references']+=1
  if (h(name),kind)not in audio:missing.append({'audio_kind':kind,'name':name.hex(),'where':where})
 db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1]
 for path in sorted((ROOT/'build/original').glob('*.lmu')):
  m=data_root(path.read_bytes())[1];used_chipsets.add(integer(m.get(1,b''),1));max_cells=max(max_cells,integer(m.get(2,b''),20)*integer(m.get(3,b''),15));resource(1,m.get(32,b''),path.name)
  for eid,e in array(m.get(81,b'')):
   for pid,p in array(e[5]):move_types[integer(p.get(31,b''))]+=1;resource(3,p.get(21,b''),f'{path.name}/{eid}/{pid}');streams.append((f'{path.name}/{eid}/{pid}',p.get(52,b'')))
 for cid,c in array(db[25]):streams.append((f'common{cid}',c.get(22,b'')))
 for tid,t in array(db[15]):
  for pid,p in array(t.get(11,b'')):streams.append((f'troop{tid}/{pid}',p.get(12,b'')))
 for aid,a in array(db[11]):resource(3,a.get(3,b''),f'actor{aid}')
 for tid,t in array(db[16]):resource(4,t.get(4,b''),f'terrain{tid}')
 for aid,a in array(db[19]):
  for tid,t in array(a.get(6,b'')):sound(fields(t.get(2,b'')).get(1,b''),1,f'animation{aid}/{tid}')
 system=fields(db[22])
 for i in range(41,53):sound(fields(system.get(i,b'')).get(1,b''),1,f'system sound{i}')
 for loc,code in streams:
  for op,name,p in rawcommands(code):
   counts[str(op)]+=1
   if op==11110:max_picture=max(max_picture,p[0]);resource(0,name,loc)
   elif op==11720:resource(1,name,loc)
   elif op==10630:resource(3,name,loc)
   elif op in(13210,):resource(4,name,loc)
   elif op==10710 and p[2]==1:resource(4,name,loc)
   elif op in(11510,10660):sound(name,0,loc)
   elif op in(11550,10670):sound(name,1,loc)
   elif op==11710:used_chipsets.add(p[0])
 for cid,c in array(db[20]):
  if cid in used_chipsets:resource(2,c.get(2,b''),f'chipset{cid}')
  elif (2,h(c.get(2,b'')))not in resources:unused_defaults.append({'type':'chipset','database_id':cid,'name_hex':c.get(2,b'').hex(),'reason':'Not selected by any source map or ChangeMapTileset command'})
 for i in range(31,39):
  name=fields(system.get(i,b'')).get(1,b'')
  if i==34 and not counts['10730']and name and (h(name),0)not in audio:unused_defaults.append({'type':'system inn music','name_hex':name.hex(),'reason':'No ShowInn commands in the original; scripted resting music is audited separately'})
  else:sound(name,0,f'system music{i}')
 # LMT begins with a direct map array, not a fields object.
 r=Reader((ROOT/'build/original/RPG_RT.lmt').read_bytes());assert r.string()==b'LcfMapTree';n=r.num();encounters=0;music_types=collections.Counter()
 for _ in range(n):
  mid=r.num();m=r.fields();encounters+=len(array(m.get(41,b'')));music_types[integer(m.get(11,b''))]+=1
  if integer(m.get(11,b''))==2:sound(fields(m.get(12,b'')).get(1,b''),0,f'map tree{mid}')
 out=ROOT/'evidence/full_features';out.mkdir(exist_ok=True)
 report={'status':'fail'if missing else 'pass','kind':'static original requirement/resource inventory; gameplay separate','source_archive_sha256':manifest['archive_sha256'],'original_map_pages':sum(move_types.values()),'original_page_move_types':dict(move_types),'autonomous_movement_needed_by_this_game':set(move_types)!={0},'random_encounter_entries':encounters,'map_music_types':dict(music_types),'max_picture_slot':max_picture,'max_map_cells':max_cells,'used_chipsets':sorted(used_chipsets),'image_references_checked':counts['image references'],'audio_references_checked':counts['audio references'],'all_referenced_resources_found':not missing,'missing':missing,'unprovided_unused_defaults':unused_defaults,'command_counts':{k:v for k,v in counts.items()if k.isdigit()},'resource_manifest_sha256':hashlib.sha256((ROOT/'build/asset_manifest.json').read_bytes()).hexdigest(),'audio_bank_sha256':hashlib.sha256(b).hexdigest(),'audio_playback_acceptance':'separate; static presence is not a passing playback test'}
 (out/'original_requirements.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='command_counts'},ensure_ascii=False,indent=2))
 assert not missing,missing
 assert set(move_types)=={0},move_types
 assert max_picture<=50 and max_cells<=2048 and not encounters
if __name__=='__main__':main()
