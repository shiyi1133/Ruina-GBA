"""Preconvert native 24x32 RPG Maker poses into ready-to-copy GBA OBJ tiles.

Each character retains every source RGB555 color and every native pixel.
The display allocates stable shared 8bpp OBJ colors as characters enter view.
"""
import hashlib,json,struct,zipfile,zlib
from pathlib import Path
import numpy as np
from PIL import Image
from project_env import ROOT,ARCHIVE
from portrait_assets import logical
from high_color_assets import rgb555,rgb8,nearest

def namehash(data):
 h=2166136261
 for b in data:h=((h^b)*16777619)&0xffffffff
 return h

def main():
 manifest=json.loads((ROOT/'build/asset_manifest.json').read_text())
 ids={r['hash']:r['image']for r in manifest['resources']if r['kind']==3}
 records=[];palettes=bytearray();tiles=bytearray();sources=[];details=[];previews=[]
 with zipfile.ZipFile(ARCHIVE)as z:
  paths=sorted((logical(n),n)for n in z.namelist()if '/CharSet/'in logical(n)and n.endswith('.xyz'))
  for path,physical in paths:
   raw=z.read(physical);w,h=struct.unpack_from('<HH',raw,4);data=zlib.decompress(raw[8:]);assert(w,h)==(288,256)
   palette=rgb555(np.frombuffer(data[:768],np.uint8).reshape(256,3));pixels=np.frombuffer(data[768:],np.uint8).reshape(h,w)
   image=ids[namehash(Path(path).stem.encode('cp932'))];sources.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'image':image})
   for index in range(8):
    source=pixels[index//4*128:(index//4+1)*128,index%4*72:(index%4+1)*72]
    colors=palette[source];alpha=source==0;unique=np.unique(colors[~alpha]);count=len(unique)
    visible=unique.tolist();assert count<=255
    own=[int(palette[0])]+[int(c)for c in visible];own+=[0]*(256-len(own));lut=np.zeros(32768,np.uint8);lut[unique]=np.arange(1,count+1,dtype=np.uint8)
    output=lut[colors];output[alpha]=0;changed=int(np.count_nonzero((np.asarray(own,np.uint16)[output]!=colors)&~alpha))
    pal_at=len(palettes);tile_at=len(tiles);palettes.extend(struct.pack('<256H',*own))
    for direction in range(4):
     for frame in range(3):
      pose=np.zeros((32,32),np.uint8);pose[:,:24]=output[direction*32:direction*32+32,frame*24:frame*24+24]
      for ty in range(4):
       for tx in range(4):
        block=pose[ty*8:ty*8+8,tx*8:tx*8+8];tiles.extend(block.tobytes())
    records.append((image,index,(len(visible)+1)&255,pal_at,tile_at))
    details.append({'image':image,'index':index,'source_colors':count,'visible_pixels':int(np.count_nonzero(~alpha)),'changed_RGB555_pixels':changed,'exact_RGB555':changed==0})
    a=Image.fromarray(rgb8(colors.ravel()).reshape(128,72,3),'RGB');b=Image.fromarray(rgb8(np.asarray(own)[output].ravel()).reshape(128,72,3),'RGB')
    pair=Image.new('RGB',(144,128));pair.paste(a,(0,0));pair.paste(b,(72,0));previews.append(pair)
 records.sort();record_at=24;palette_at=record_at+len(records)*12;tile_at=palette_at+len(palettes)
 bank=struct.pack('<6I',0x4a424f52,len(records),record_at,palette_at,tile_at,1024)+b''.join(struct.pack('<HBBII',*r)for r in records)+palettes+tiles
 (ROOT/'build/characters.bin').write_bytes(bank)
 report={'format':'native 24x32 actors, unreduced 8bpp RGB555 colors, all 12 poses pre-tiled','characters':len(records),'poses':len(records)*12,'bytes':len(bank),'exact_characters':sum(d['exact_RGB555']for d in details),'changed_RGB555_pixels':sum(d['changed_RGB555_pixels']for d in details),'visible_pixels':sum(d['visible_pixels']for d in details),'sources':sources,'characters_detail':details,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'bank_sha256':hashlib.sha256(bank).hexdigest()}
 (ROOT/'build/characters_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 proof=ROOT/'evidence/optimization_20261022/characters';proof.mkdir(parents=True,exist_ok=True)
 sheet=Image.new('RGB',(144*8,128*9));
 for i,pair in enumerate(previews):sheet.paste(pair,(i%8*144,i//8*128))
 sheet.save(proof/'source_left_OBJ_right.png')
 print(json.dumps({k:v for k,v in report.items()if k not in('sources','characters_detail')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
