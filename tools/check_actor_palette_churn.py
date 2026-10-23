"""Changing visible actor sets reclaim stale OBJ colors without spatial loss."""
import hashlib,json,struct,zipfile,zlib
import numpy as np
from PIL import Image
from project_env import ROOT,ARCHIVE
from portrait_assets import logical
from gba_fixture import fixture
from drive_opening import Emulator

def main():
 bank=(ROOT/'build/characters.bin').read_bytes();h=struct.unpack_from('<6I',bank);records=[struct.unpack_from('<HBBII',bank,h[2]+i*12)for i in range(h[1])];meta=json.loads((ROOT/'build/characters_manifest.json').read_text());original={}
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()}
  for s in meta['sources']:
   raw=z.read(names[s['path']]);w,hh=struct.unpack_from('<HH',raw,4);d=zlib.decompress(raw[8:]);original[s['image']]=(np.frombuffer(d,np.uint8,offset=768).reshape(hh,w),np.frombuffer(d,np.uint8,768).reshape(256,3)>>3)
 rom,elf,production=fixture('tests/actor_palette_churn_gba.c','actor_palette_churn',{'video':'tests/native_palette_video.c'});digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/actor_palette_churn'/digest[:12];out.mkdir(parents=True,exist_ok=True);e=Emulator(rom=rom,elf=elf);rows=[]
 try:
  for stage in range(h[1]*2):
   for _ in range(3000):
    if e.debug()[14]==stage+1:break
    e.frames(1)
   else:raise AssertionError((stage,e.debug()))
   e.frames(2);path=out/'current.png';e.shot(path);screen=np.asarray(Image.open(path).convert('RGB'))>>3;different=visible=0;actors=[]
   for k,index in enumerate([stage%h[1],(stage*17+35)%h[1],0]):
    image,character=records[index][:2];p,pal=original[image];direction=(stage+k)%4;source=p[character//4*128+direction*32:character//4*128+direction*32+32,character%4*72+24:character%4*72+48];mask=source!=0;actual=screen[50:82,30+k*70:54+k*70];different+=int(np.count_nonzero(np.any(actual!=pal[source],axis=2)&mask));visible+=int(mask.sum());actors.append([image,character,direction])
   row={'stage':stage+1,'actors':actors,'visible_source_pixels':visible,'different_RGB555_pixels':different};rows.append(row)
   if different or stage in(0,15,40,80,h[1]*2-1):e.shot(out/f'{stage+1:03}.png')
   assert not different,row;e.frames(2,1);e.frames(2)
  rebuilds=struct.unpack('<I',e.memory(e.symbols['object_palette_rebuilds'],4))[0];assert rebuilds>0;commits=struct.unpack('<3I',e.memory(e.symbols['video_native_commit_metrics'],12));assert not commits[0];result={'status':'pass','scope':'controlled actual GBA; three original characters shown together while traversing all72 source characters twice; current poses compared to original XYZ RGB555','views':len(rows),'actors_checked':len(rows)*3,'OBJ_palette_reclaims':rebuilds,'native_commit_metrics':commits,'different_RGB555_pixels':sum(r['different_RGB555_pixels']for r in rows),'production_rom_sha256':production,'fixture_sha256':digest,'rows':rows,'physical_hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'},ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
