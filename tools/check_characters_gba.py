"""Compare native OBJ textures and actual LCD output with original XYZ pixels."""
import hashlib,json,struct,zipfile,zlib
from pathlib import Path
import numpy as np
from PIL import Image
from project_env import ARCHIVE,ROOT
from portrait_assets import logical
from gba_fixture import fixture
from drive_opening import Emulator

def main():
 manifest=json.loads((ROOT/'build/characters_manifest.json').read_text());original={}
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()}
  for record in manifest['sources']:
   raw=z.read(names[record['path']]);w,h=struct.unpack_from('<HH',raw,4);d=zlib.decompress(raw[8:]);palette=np.frombuffer(d[:768],np.uint8).reshape(256,3);pixels=np.frombuffer(d[768:],np.uint8).reshape(h,w)
   original[record['image']]=(palette,pixels)
 bank=(ROOT/'build/characters.bin').read_bytes();magic,count,records,palettes,tiles,stride=struct.unpack_from('<6I',bank);assert magic==0x4a424f52 and stride==1024
 cases=[];bank_checked=0
 for i in range(count):
  image,index,colors,pal,pose=struct.unpack_from('<HBBII',bank,records+i*12);palette,pixels=original[image];local=np.frombuffer(bank,np.dtype('<u2'),256,palettes+pal)
  for direction in range(4):
   for frame in range(3):
    source=pixels[index//4*128+direction*32:index//4*128+direction*32+32,index%4*72+frame*24:index%4*72+frame*24+24];expected=palette[source]>>3;mask=source!=0
    tiled=np.frombuffer(bank,np.uint8,1024,tiles+pose+(direction*3+frame)*1024).reshape(4,4,8,8).transpose(0,2,1,3).reshape(32,32)[:,:24]
    rgb=local[tiled];packed=(expected[:,:,0].astype(np.uint16)|(expected[:,:,1].astype(np.uint16)<<5)|(expected[:,:,2].astype(np.uint16)<<10))
    assert np.array_equal(rgb[mask],packed[mask]) and np.array_equal(tiled==0,~mask);bank_checked+=1
  cases.append((image,index))
 rom,elf,production=fixture('tests/characters_gba.c','native_characters',{'video':'tests/native_palette_video.c'});digest=hashlib.sha256(rom.read_bytes()).hexdigest();out=ROOT/'evidence/optimization_20261022/characters'/digest[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf);rows=[]
 try:
  for i,(image,index)in enumerate(cases):
   for _ in range(800):
    if e.debug()[14]==i+1:break
    e.frames(1)
   else:raise AssertionError((i,e.debug()))
   e.frames(2);path=out/'current.png';e.shot(path);screen=np.asarray(Image.open(path).convert('RGB'));palette,pixels=original[image];different=visible=0
   for direction in range(4):
    source=pixels[index//4*128+direction*32:index//4*128+direction*32+32,index%4*72+24:index%4*72+48];mask=source!=0;actual=screen[50:82,30+direction*45:54+direction*45]
    different+=int(np.count_nonzero(np.any((actual>>3)!=(palette[source]>>3),axis=2)&mask));visible+=int(mask.sum())
   if i%8==0 or different:e.shot(out/f'{i:02}_image{image}_character{index}.png')
   rows.append({'image':image,'index':index,'directions':4,'source_visible_pixels':visible,'different_RGB555_pixels':different})
   e.frames(2,1);e.frames(2)
  result={'status':'pass'if not any(r['different_RGB555_pixels']for r in rows)else'fail','original_bank_poses_checked':bank_checked,'LCD_directions_checked':len(rows)*4,'different_RGB555_pixels':sum(r['different_RGB555_pixels']for r in rows),'production_rom_sha256':production,'fixture_sha256':digest,'bank_sha256':hashlib.sha256(bank).hexdigest(),'rows':rows,'scope':'isolated original characters; actual gameplay visibility and combined palette checked separately','physical_hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':result['status'],'report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'},ensure_ascii=False,indent=2),flush=True)
  assert result['status']=='pass'
 finally:e.close()

if __name__=='__main__':main()
