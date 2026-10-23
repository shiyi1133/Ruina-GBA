"""All native panoramas: actual GBA crops versus independent original XYZ.
The three palettes which exceed the reserved UI budget are reported as fitted,
then checked against their declared nearest RGB555 colors, not called exact.
"""
import ctypes as C,hashlib,json,struct,zipfile,zlib
import numpy as np
from PIL import Image
from project_env import ROOT,ARCHIVE
from portrait_assets import logical
from gba_fixture import fixture
from drive_opening import Emulator
from high_color_assets import nearest

def main():
 meta=json.loads((ROOT/'build/asset_manifest.json').read_text());resources=[r for r in meta['resources']if r['kind']==1];sources={};cases=[]
 def namehash(s):
  h=2166136261
  for b in s:h=((h^b)*16777619)&0xffffffff
  return h
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()};lookup={namehash(n.rsplit('/',1)[1][:-4].encode('cp932')):n for n in names if '/Panorama/'in n and n.endswith('.xyz')}
  for r in resources:
   path=lookup[r['hash']];raw=z.read(names[path]);w,h=struct.unpack_from('<HH',raw,4);d=zlib.decompress(raw[8:]);idx=np.frombuffer(d,np.uint8,offset=768).reshape(h,w);rgb=np.frombuffer(d,np.uint8,768).reshape(256,3).astype(np.uint16)>>3;palette=rgb[:,0]|(rgb[:,1]<<5)|(rgb[:,2]<<10);pixels=palette[idx];sources[r['image']]=(pixels,path)
   for x,y in dict.fromkeys([(0,0),(max(0,w-240)//8*8,max(0,h-160)//8*8),(max(0,w-240)//16*8,max(0,h-160)//16*8),(min(8,max(0,w-240))//8*8,min(16,max(0,h-160))//8*8)]):cases.append((r['image'],x,y))
 (ROOT/'build/panorama_matrix_config.h').write_text('static const unsigned panorama_matrix[][3]={'+','.join('{%d,%d,%d}'%r for r in cases)+'};\n');rom,elf,production=fixture('tests/panorama_matrix_gba.c','panorama_matrix',{'video':'tests/native_palette_video.c'});digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/panorama_matrix'/digest[:12];out.mkdir(parents=True,exist_ok=True);e=Emulator(rom=rom,elf=elf);rows=[];mask=np.ones((160,240),bool)
 for x,y in[(116,2),(230,76),(116,150),(2,76)]:mask[y:y+8,x:x+8]=False
 try:
  for stage,(image,x,y)in enumerate(cases,1):
   for _ in range(3000):
    if e.debug()[14]==stage:break
    e.frames(1)
   else:raise AssertionError(('stage',stage,e.debug()))
   e.frames(2);pal=np.frombuffer(e.memory(0x05000000,512),dtype='<u2');pixels,path=sources[image];expected=np.full((160,240),pal[14],np.uint16);crop=pixels[y:y+160,x:x+240];expected[:crop.shape[0],:crop.shape[1]]=crop;unique,inverse=np.unique(expected,return_inverse=True);displayed=pal[nearest(unique,pal)][inverse].reshape(160,240);actualpath=out/'current.png';e.shot(actualpath);rgb=np.asarray(Image.open(actualpath).convert('RGB'))>>3;actual=rgb[...,0].astype(np.uint16)|(rgb[...,1].astype(np.uint16)<<5)|(rgb[...,2].astype(np.uint16)<<10);different=int(np.count_nonzero((actual!=displayed)&mask));original_difference=int(np.count_nonzero((actual!=expected)&mask));row={'stage':stage,'image':image,'source':path,'camera':[x,y],'display_different_pixels':different,'original_RGB555_different_pixels':original_difference,'render_ticks_16384Hz':struct.unpack('<I',e.memory(e.symbols['panorama_render_timing']+4,4))[0]if 'panorama_render_timing'in e.symbols else None,'whole_tile_counts':list(struct.unpack('<2I',e.memory(e.symbols['native_whole_tile_metrics'],8)))if 'native_whole_tile_metrics'in e.symbols else None};rows.append(row)
   if different or stage in(1,2,5,len(cases))or(original_difference and x==0 and y==0):e.shot(out/f'{stage:03}_image{image}_{x}_{y}.png')
   assert not different,row;e.frames(2,1);e.frames(2)
  result={'status':'pass','panoramas':len(resources),'native_GBA_crops':len(cases),'pixels_checked':int(mask.sum())*len(cases),'display_different_pixels':sum(r['display_different_pixels']for r in rows),'original_RGB555_different_pixels':sum(r['original_RGB555_different_pixels']for r in rows),'scope':'actual GBA cropped native pictures against untouched original XYZ; palette budget approximations separately counted; UI arrows masked out','production_rom_sha256':production,'fixture_sha256':digest,'image_bank_sha256':hashlib.sha256((ROOT/'build/high_color_blobs.bin').read_bytes()).hexdigest(),'rows':rows,'physical_hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':'pass','report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'},ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
