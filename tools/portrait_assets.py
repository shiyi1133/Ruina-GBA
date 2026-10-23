"""Preserve original 48x48 indexed faces and each sheet's own 256 colors.
OBJ palettes are independent of the reduced background palette. No resizing
or additional color quantization is applied to these portrait pixels.
"""
import hashlib,json,struct,zipfile,zlib
from pathlib import Path
from project_env import ROOT,ARCHIVE

def logical(n):
 try:return n.encode('gbk').decode('cp932')
 except UnicodeError:return n

def main():
 m=json.loads((ROOT/'build/asset_manifest.json').read_text());labels=m['images']
 palettes=bytearray();tiles=bytearray();records=[];sources=[]
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()}
  paths=sorted(n for n in names if '/FaceSet/'in n and n.endswith('.xyz'))
  for sheet,path in enumerate(paths):
   raw=z.read(names[path]);w,h=struct.unpack_from('<HH',raw,4);data=zlib.decompress(raw[8:]);assert w>=192 and h>=192
   colors=data[:768];pixels=data[768:];assert len(pixels)==w*h
   sources.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest()})
   for r,g,b in zip(colors[::3],colors[1::3],colors[2::3]):palettes.extend(struct.pack('<H',(r>>3)|((g>>3)<<5)|((b>>3)<<10)))
   for index in range(16):
    label='hero'+str(index)if Path(path).stem=='顔絵主役'else f'face{sheet}_{index}'
    image=labels.index(label);offset=len(tiles);x0=index%4*48;y0=index//4*48
    # Nine 16x16 OBJ squares, each containing four 8x8 tiles in 1D order.
    for by in range(3):
     for bx in range(3):
      for ty in range(2):
       for tx in range(2):
        for y in range(8):
         at=(y0+by*16+ty*8+y)*w+x0+bx*16+tx*8
         tiles.extend(pixels[at:at+8])
    records.append((image,sheet,offset))
 header_size=20;descriptors=header_size;palette_offset=descriptors+len(records)*8;tile_offset=palette_offset+len(palettes)
 bank=struct.pack('<5I',0x43414652,len(records),descriptors,palette_offset,tile_offset)+b''.join(struct.pack('<HHI',*r)for r in records)+palettes+tiles
 (ROOT/'build/portraits.bin').write_bytes(bank)
 report={'format':'original indexed 48x48 faces in 8-bit OBJ tiles, original sheet palette converted only to GBA RGB555','portraits':len(records),'sheets':len(paths),'bytes':len(bank),'additional_lossy_resize':False,'additional_color_reduction':False,'transparent_palette_index':0,'sources':sources,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'bank_sha256':hashlib.sha256(bank).hexdigest()}
 (ROOT/'build/portraits_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='sources'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
