"""Real buttons: visible entrance, arrow limits, map panning and investigation."""
import hashlib,json,struct
from drive_opening import ROOT,Emulator

def main():
 digest=hashlib.sha256((ROOT/'build/废都物语_GBA_开篇开发验证版.gba').read_bytes()).hexdigest()
 out=ROOT/'evidence/hardware_scroll/navigation'/digest[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav');checks={};rows=[]
 def observe(name):
  e.frames(2);e.shot(out/(name+'.png'))
  camera=tuple(struct.unpack('<i',e.memory(e.symbols[n],4))[0]for n in ('render_camera_x','render_camera_y'))
  metrics=list(struct.unpack('<8I',e.memory(e.symbols['map_video_metrics'],32)))
  arrows=[struct.unpack('<3H',e.memory(0x07000000+(124+i)*8,6))for i in range(4)]
  expected=[768+(0 if camera[1]>0 else 2),772+(0 if camera[0]<80 else 2),776+(0 if camera[1]<80 else 2),780+(0 if camera[0]>0 else 2)]
  row={'name':name,'camera':camera,'metrics':metrics,'arrows':arrows,'arrow_tiles_match_bounds':[a[2]==b for a,b in zip(arrows,expected)]};rows.append(row);return row
 def position():return e.memory(e.symbols['game']+29768,12)
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(120)
  assert e.debug()[15]==4,e.debug()
  a=observe('entrance_marked_on_load');start=position()
  markers=[struct.unpack('<H',e.memory(0x07000000+(49+i)*8,2))[0]for i in range(71)]
  checks['available_entrance_shown_without_pressing_LR']=any(not v&0x200 for v in markers)
  # A saved zero selection is now deliberately local mode. Explicit L/R
  # chooses the remote entrance before testing routing and selection blinking.
  e.key(256);assert e.debug()[11]==1,e.debug()
  e.key(256|64);b=observe('pan_up');checks['browse_does_not_move_party']=position()==start
  e.key(256|32);c=observe('top_left_boundary')
  e.key(256|128);d=observe('bottom_left_boundary')
  e.key(256|16);f=observe('bottom_right_boundary')
  checks['camera_moves_in_four_directions']=b['camera'][1]<a['camera'][1] and c['camera'][0]<b['camera'][0] and d['camera'][1]>c['camera'][1] and f['camera'][0]>d['camera'][0]
  checks['arrows_lit_or_gray_follow_boundaries']=all(all(r['arrow_tiles_match_bounds'])for r in rows)
  before=f['metrics'][0];tiles=set()
  for _ in range(10):
   e.frames(12);tiles.add(struct.unpack('<H',e.memory(0x07000000+120*8+4,2))[0])
  after=observe('selection_blink_without_background_repaint')
  checks['selection_blinks_as_hardware_sprite']=len(tiles)==2
  checks['idle_blink_has_no_background_upload']=after['metrics'][0]==before
  e.key(1)
  for _ in range(240):
   q=e.debug();assert q[0]!=0x4641554c and q[15]!=5,q
   phase=struct.unpack('<i',e.memory(e.symbols['game']+8+41*4,4))[0]
   if q[15]==4 and phase==2:break
   if q[15]in(1,2):e.key(1)
   else:e.frames(30)
  else:raise AssertionError(('entrance not entered',e.debug()))
  e.frames(2);e.shot(out/'entrance_investigated.png');checks['marked_entrance_can_be_investigated']=True
  result={'status':'pass'if all(checks.values())else'fail','rom_sha256':digest,'checks':checks,'observations':rows,
          'input':'actual emulated buttons; ordinary save, no memory/register writes or instant states','commands':e.log,'hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'report':str((out/'result.json').relative_to(ROOT)),'status':result['status']},ensure_ascii=False,indent=2))
  print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2),flush=True);assert result['status']=='pass',checks
 except Exception as error:
  e.shot(out/'failed.png');(out/'failure.json').write_text(json.dumps({'status':'fail','error':str(error),'debug':e.debug(),'commands':e.log},ensure_ascii=False,indent=2));raise
 finally:e.close()

if __name__=='__main__':main()
