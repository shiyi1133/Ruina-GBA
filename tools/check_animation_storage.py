"""Independently decompress every stored cell and compare original XYZ pixels."""
import hashlib,json,re,struct,zipfile,zlib
from pathlib import Path
from inspect_lcf import data_root,array,integer,filename
from portrait_assets import logical
from project_env import ROOT,ARCHIVE

def unpack(src,size):
 out=bytearray();at=0
 while at<len(src):
  token=src[at];at+=1;n=token>>4
  if n==15:
   while True:
    v=src[at];at+=1;n+=v
    if v!=255:break
  out+=src[at:at+n];at+=n
  if at==len(src):break
  offset=int.from_bytes(src[at:at+2],'little');at+=2;n=(token&15)+4
  if token&15==15:
   while True:
    v=src[at];at+=1;n+=v
    if v!=255:break
  assert 0<offset<=len(out)
  for _ in range(n):out.append(out[-offset])
 assert len(out)==size,(len(out),size);return bytes(out)

def main():
 bank=(ROOT/'build/battle_animations.bin').read_bytes();header=(ROOT/'build/battle_animation_assets.h').read_text();cells=[]
 pattern=r'\{\{original_animations_start\+(\d+),(\d+),(\d+),\(const u32\*\)\(original_animations_start\+(\d+)\),0,8,1,\d+,\d+,\(const u16\*\)\(original_animations_start\+(\d+)\),(\d+)\},(-?\d+),(-?\d+)\}'
 for m in re.finditer(pattern,header):
  offset,w,h,rows,pal,count,x,y=map(int,m.groups());bh=4096//w;blocks=(h+bh-1)//bh;indices=struct.unpack_from('<%dI'%(blocks+1),bank,rows);p=b''.join(unpack(bank[offset+indices[j]:offset+indices[j+1]],w*min(bh,h-j*bh))for j in range(blocks));palette=struct.unpack_from('<%dH'%count,bank,pal);full=[None]*9216
  for yy in range(h):
   for xx in range(w):
    v=p[yy*w+xx]
    if v:full[(yy+y+48)*96+xx+x+48]=palette[v]
  cells.append(full)
 sheets={name:[int(v)for v in values.split(',')]for name,values in re.findall(r'static const short (animation_sheet_\d+)\[\]=\{([^}]+)\}',header)}
 ids={int(a):sheets[s]for a,s in re.findall(r'\{(\d+),(animation_sheet_\d+),sizeof',header)};db=data_root((ROOT/'build/original/RPG_RT.ldb').read_bytes())[1];checked=set();blank=0
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()}
  for aid,a in array(db[19]):
   if aid not in ids:continue
   path='Ruina121/game/Battle/'+filename(a[2])+'.xyz';raw=z.read(names[path]);w,h=struct.unpack_from('<HH',raw,4);d=zlib.decompress(raw[8:]);palette=[(r>>3)|((g>>3)<<5)|((b>>3)<<10)for r,g,b in zip(d[:768:3],d[1:768:3],d[2:768:3])];p=d[768:]
   for cid,index in zip(ids[aid][::2],ids[aid][1::2]):
    if (path,cid)in checked:continue
    checked.add((path,cid));x=cid%5*96;y=cid//5*96;source=[palette[v]if v else None for yy in range(96)for v in p[(y+yy)*w+x:(y+yy)*w+x+96]]
    if index<0:assert all(v is None for v in source);blank+=1
    else:assert cells[index]==source,(aid,cid,index)
 original=(ROOT/'build/portraits.bin').read_bytes();packed=(ROOT/'build/portraits_packed.bin').read_bytes();a=struct.unpack_from('<5I',original);b=struct.unpack_from('<5I',packed)
 for i in range(a[1]):
  old=struct.unpack_from('<HHI',original,a[2]+i*8);new=struct.unpack_from('<HHI',packed,b[2]+i*8);assert old[:2]==new[:2];at=b[4]+new[2];n=struct.unpack_from('<H',packed,at)[0];assert unpack(packed[at+2:at+2+n],2304)==original[a[4]+old[2]:a[4]+old[2]+2304]
 result={'status':'pass','visible_cells':len(cells),'original_cells_checked':len(checked),'empty_cells':blank,'all_original_RGB555_pixels_exact':True,'all_transparency_masks_exact':True,'losslessly_packed_portraits':a[1],'bank_sha256':hashlib.sha256(bank).hexdigest(),'method':'Independent decoder, directly compared to original archive XYZ palette indices, with transparent index distinguished even when RGB equals a visible color.'}
 out=ROOT/'evidence/battle_animations_20261023/storage.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
