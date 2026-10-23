"""Observe every LCD frame during actual cursor, camera and walking inputs.

Settled screenshots cannot detect an object list that vanishes while the next
view is being decoded. This regression deliberately observes intermediate
frames as well as the completed view. No emulator state is modified.
"""
import hashlib,json,struct,sys
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator

def main():
 baseline='--baseline'in sys.argv
 folder=ROOT/'history/pre_cursor_fix_20261021'if baseline else ROOT/'build'
 rom=folder/'废都物语_GBA_开篇开发验证版.gba';elf=folder/'ruina_opening_dev.elf'
 digest=hashlib.sha256(rom.read_bytes()).hexdigest()
 out=ROOT/'evidence/cursor_flash'/digest[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(ROOT/'evidence/save_cold_load/ordinary.sav',rom=rom,elf=elf);rows=[];checks={}
 def value(name):return struct.unpack('<I',e.memory(e.symbols[name],4))[0]
 try:
  e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(120);e.key(256);e.key(1)
  for _ in range(200):
   d=e.debug();phase=struct.unpack('<i',e.memory(e.symbols['game']+172,4))[0]
   if d[15]==4 and phase==2:break
   if d[15]in(1,2):e.key(1)
   else:e.frames(30)
  else:raise AssertionError(('phase2',e.debug()))
  e.frames(2);e.shot(out/'before.png')
  sequences=[('select_next',256,3),('select_next_again',256,3),('select_previous',512,3),
             ('browse_up',320,12),('browse_left',288,12),('browse_down',384,12),
             ('browse_right',272,12),('walk_up',64,3),('walk_down',128,3),
             ('walk_left',32,3),('walk_right',16,3)]
  for label,key,hold in sequences:
   for i in range(150):
    e.frames(1,key if i<hold else 0)
    oam=struct.unpack('<512H',e.memory(0x07000000,1024))
    arrows=all(not oam[(124+j)*4]&0x200 for j in range(4))
    selected=not oam[120*4]&0x200
    screen=struct.unpack('<H',e.memory(0x04000050,2))[0]
    row={'sequence':label,'frame':i,'arrows_present':arrows,'selection_present':selected,
         'brightness_effect':screen,'presented_revision':value('world_presented_revision')}
    # Screen shade is write-only on hardware, so also observe actual LCD pixels.
    if not arrows or screen or i in(0,50,149):
     path=out/'observed_frame.png';e.shot(path)
     pixels=np.asarray(Image.open(path).convert('RGB'))
     row['black_pixels']=int((pixels.max(axis=2)<8).sum())
     if not arrows or row['black_pixels']>38000:
      if sum('failure_image'in r for r in rows)<8:
       row['failure_image']=label+f'_{i:03}.png';e.shot(out/row['failure_image'])
    rows.append(row)
   e.shot(out/(label+'.png'))
   assert e.debug()[15]==4 and e.debug()[9]==23,e.debug()
   print(label,'missing arrows',sum(not r['arrows_present']for r in rows if r['sequence']==label),
         'black frames',sum(r.get('black_pixels',0)>38000 for r in rows if r['sequence']==label),flush=True)
  checks['all_native_commits_within_VBlank']=not struct.unpack('<3I',e.memory(e.symbols['video_native_commit_metrics'],12))[0]if'video_native_commit_metrics'in e.symbols else True
  checks['no_transient_loss_of_edge_arrows']=all(r['arrows_present']for r in rows)
  checks['no_black_frames_during_navigation']=not any(r.get('black_pixels',0)>38000 for r in rows)
  checks['navigation_does_not_apply_screen_shading']=not any(r['brightness_effect']for r in rows)
  # Keep observing the selected marker for two blink periods. It may change
  # color, but the border and static background must remain on screen.
  e.key(256);before=value('map_video_metrics');tiles=set()
  for _ in range(90):
   e.frames(1);tiles.add(struct.unpack('<H',e.memory(0x07000000+120*8+4,2))[0])
  checks['idle_selection_blink_does_not_repaint_BG']=value('map_video_metrics')==before
  checks['selection_border_animates']=len(tiles)==2
  result={'status':'pass'if all(checks.values())else'fail','rom_sha256':digest,'checks':checks,
          'frames_observed':len(rows),'missing_arrow_frames':sum(not r['arrows_present']for r in rows),
          'black_frames':sum(r.get('black_pixels',0)>38000 for r in rows),
          'kind':'actual production cartridge, genuine ordinary save and buttons, every intermediate LCD frame observed',
          'hardware':'not_run','rows':rows,'commands':e.log}
  (out/'continuity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
  if not baseline:(out.parent/'latest_attempt.json').write_text(json.dumps({'report':str((out/'continuity.json').relative_to(ROOT)),'status':result['status']},ensure_ascii=False,indent=2))
  print(json.dumps({k:v for k,v in result.items()if k not in('rows','commands')},ensure_ascii=False,indent=2),flush=True)
  if not baseline:assert result['status']=='pass',checks
 finally:e.close()

if __name__=='__main__':main()
