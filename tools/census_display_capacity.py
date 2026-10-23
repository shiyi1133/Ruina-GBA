"""Conservative static page union at every 8-pixel native-map camera.
Mutually exclusive event pages are combined on purpose. Script relocations and
graphic overrides need dynamic gameplay coverage and are not certified here.
"""
import hashlib,json
from inspect_lcf import ROOT,data_root,array,integer,commands

def main():
 rows=[];excluded={13,14,15,16,17,18,19,22}
 for path in sorted((ROOT/'build/original').glob('*.lmu')):
  mid=int(path.stem[3:])
  if mid<3 or mid in excluded:continue
  m=data_root(path.read_bytes())[1];w=integer(m.get(2,b''),20);h=integer(m.get(3,b''),15);actors=[];points=[]
  for eid,event in array(m.get(81,b'')):
   x=integer(event.get(2,b''))*16;y=integer(event.get(3,b''))*16;poses=set();point=False
   for pid,page in array(event.get(5,b'')):
    graphic=page.get(21,b'');index=integer(page.get(22,b''));direction=integer(page.get(23,b''),2)
    if graphic:poses.add((graphic.hex(),index,direction))
    if integer(page.get(33,b''))==0 and(graphic or index>0)and any(c['code']not in(0,10,12410,22410)for c in commands(page.get(52,b''))):point=True
   if poses:actors.append((eid,x-4,y-16,poses))
   if point:points.append((eid,x+4,y+4))
  worst_actors=worst_textures=worst_points=0;at_actors=at_textures=at_points=None;views=0
  for cy in range(0,max(0,h*16-160)+1,8):
   for cx in range(0,max(0,w*16-240)+1,8):
    views+=1;visible=[r for r in actors if -32<r[1]-cx<240 and -32<r[2]-cy<160];unique=set().union(*(r[3]for r in visible))if visible else set();actor_bound=len(visible)+1;texture_bound=min(len(visible),len(unique))+1;p=[r[0]for r in points if -7<=r[1]-cx<240 and -7<=r[2]-cy<160]
    if actor_bound>worst_actors:worst_actors=actor_bound;at_actors={'camera':[cx,cy],'event_IDs':[r[0]for r in visible],'includes_one_possible_player':True}
    if texture_bound>worst_textures:worst_textures=texture_bound;at_textures={'camera':[cx,cy],'event_IDs':[r[0]for r in visible],'includes_one_possible_player':True}
    if len(p)>worst_points:worst_points=len(p);at_points={'camera':[cx,cy],'event_IDs':p}
  rows.append({'map':mid,'views':views,'all_pages_actor_upper_bound':worst_actors,'all_pages_declared_pose_upper_bound':worst_textures,'all_pages_point_upper_bound':worst_points,'worst_actors':at_actors,'worst_poses':at_textures,'worst_points':at_points})
 limits={'actor_objects':48,'pose_texture_slots':24,'visible_point_objects':71};maxima={'actors':max(r['all_pages_actor_upper_bound']for r in rows),'declared_poses':max(r['all_pages_declared_pose_upper_bound']for r in rows),'points':max(r['all_pages_point_upper_bound']for r in rows)}
 report={'status':'measured_conservative_static_bounds','source_LCF_sha256':hashlib.sha256((ROOT/'build/original_lcf.bin').read_bytes()).hexdigest(),'source_script_sha256':hashlib.sha256(__import__('pathlib').Path(__file__).read_bytes()).hexdigest(),'native_maps':len(rows),'camera_views':sum(r['views']for r in rows),'limits':limits,'upper_bounds':maxima,'all_static_actor_unions_fit':maxima['actors']<=limits['actor_objects'],'all_static_declared_pose_unions_fit':maxima['declared_poses']<=limits['pose_texture_slots'],'all_static_point_unions_fit':maxima['points']<=limits['visible_point_objects'],'double_buffer_all_declared_poses_fit':maxima['declared_poses']*2<=limits['pose_texture_slots'],'scope':'all source pages, mutually exclusive pages combined, every 8px camera; actual pages are condition-dependent. Forced script relocations, sprite overrides and direction changes are excluded. Not a full campaign capacity guarantee.','rows':rows}
 out=ROOT/'evidence/optimization_20261022/display_capacity';out.mkdir(parents=True,exist_ok=True);(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='rows'},ensure_ascii=False,indent=2));print('largest actor unions',json.dumps(sorted(rows,key=lambda r:-r['all_pages_actor_upper_bound'])[:5],ensure_ascii=False))
if __name__=='__main__':main()
