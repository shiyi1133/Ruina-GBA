"""Preserve every original battle cell, RGB555 color and transparent pixel.

Only empty margins and duplicate RGB555 indices are removed. LZ4 blocks fit
the existing 4 KiB decoder workspace. Native faces replace the unused smaller
face copies and their original OBJ pixels are losslessly packed to make room.
"""
import ctypes as C,ctypes.util,hashlib,json,re,struct,zipfile,zlib
from pathlib import Path
from project_env import ROOT,ARCHIVE
from inspect_lcf import data_root,array,integer,filename
from portrait_assets import logical
from image_codec import encode_lz4

def compressor():
 try:
  lib=C.CDLL(ctypes.util.find_library('lz4'));f=lib.LZ4_compress_HC
  f.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int];f.restype=C.c_int
  def compress(b):
   src=C.create_string_buffer(b);dst=C.create_string_buffer(len(b)+128)
   n=f(src,dst,len(b),len(dst),12);assert n;return dst.raw[:n]
  return compress
 except (OSError,AttributeError,TypeError):return encode_lz4

def faces(compress):
 out=ROOT/'build';raw=(out/'portraits.bin').read_bytes();h=struct.unpack_from('<5I',raw)
 packed=bytearray(raw[:h[4]]);records={}
 for i in range(h[1]):
  image,sheet,offset=struct.unpack_from('<HHI',raw,h[2]+i*8)
  encoded=compress(raw[h[4]+offset:h[4]+offset+2304]);at=len(packed)-h[4]
  struct.pack_into('<I',packed,h[2]+i*8+4,at);packed+=struct.pack('<H',len(encoded))+encoded
  records[image]=(sheet,h[4]+at,offset)
 (out/'portraits_packed.bin').write_bytes(packed)
 s=(out/'assets.c').read_text()
 match=re.search(r'const Image images\[\d*\]=\{(.*?)\};',s,re.S)
 images=re.findall(r'\{([^{}]+)\}',match[1]);keep=set();remove=set();tiled_names=set()
 rows={m[1]:[int(v)for v in m[2].split(',')] for m in re.finditer(r'const unsigned int (rows_\w+)\[\d+\]=\{([^}]+)\};',s)}
 for i,img in enumerate(images):
  f=img.split(',')
  if f[5]=='6':
   tiled_names.add(f[3]);(remove if i in records else keep).update(rows[f[3]])
 bank=(out/'high_color_blobs.bin').read_bytes();assembly=(out/'high_color_blobs.s').read_text()
 lines=assembly.splitlines();old_size=int(next(v for v in lines if '.incbin' in v).rsplit(',',1)[1]);pool=bytearray();mapping={}
 for ref in sorted(keep,key=lambda v:v&0xffffff):
  at=ref&0xffffff;size=(ref>>24)or 64;mapping[ref]=len(pool)|(ref&0xff000000);pool+=bank[at:at+size]
 for name,refs in rows.items():
  if name not in tiled_names:continue
  if not all(v in mapping for v in refs):
   s=re.sub(r'const unsigned int '+name+r'\[\d+\]=\{[^}]+\};\n?','',s)
  else:
   replacement='const unsigned int '+name+'['+str(len(refs))+']={'+','.join(str(mapping[v])for v in refs)+'};'
   s=re.sub(r'const unsigned int '+name+r'\[\d+\]=\{[^}]+\};',lambda _:replacement,s)
 palettes={tuple(map(int,m[2].split(','))):m[1]for m in re.finditer(r'const unsigned short (color_palette_\d+)\[\d+\]=\{([^}]+)\};',s)}
 for i,(sheet,offset,original_offset) in records.items():
  # Preserve the existing 36px picture API too. Gameplay portrait() still
  # reads all 48px native pixels directly; these old IDs need no second bank.
  palette=struct.unpack_from('<256H',raw,h[3]+sheet*512);data=raw[h[4]+original_offset:h[4]+original_offset+2304];visible=set()
  for yy in range(36):
   y=[0, 2, 3, 4, 5, 7, 8, 10, 11, 12, 14, 15, 16, 18, 19, 20, 21, 23, 24, 25, 27, 28, 29, 31, 32, 33, 35, 36, 38, 39, 40, 42, 43, 44, 46, 47][yy]
   for xx in range(36):
    x=[0, 2, 3, 4, 5, 7, 8, 10, 11, 12, 14, 15, 16, 18, 19, 20, 21, 23, 24, 25, 27, 28, 29, 31, 32, 33, 35, 36, 38, 39, 40, 42, 43, 44, 46, 47][xx];tile=(y//16*3+x//16)*4+(y%16//8)*2+x%16//8
    visible.add(palette[data[tile*64+y%8*8+x%8]])
  colors=sorted(visible);symbol=palettes[tuple(colors+[0]*(256-len(colors)))]
  images[i]=f'original_portraits_start+{offset},36,36,(const u32*)(original_portraits_start+{h[3]+sheet*512}),0,9,0,36,36,{symbol},{len(colors)}' 
 # Locate again after row-array removal.
 match=re.search(r'const Image images\[\d*\]=\{(.*?)\};',s,re.S)
 s=s[:match.start(1)]+','.join('{'+v+'}'for v in images)+s[match.end(1):]
 if '/* Native face storage */' not in s:s='/* Native face storage */\nextern const unsigned char original_portraits_start[];\n'+s
 (out/'assets.c').write_text(s)
 def shift(m):
  at,size=map(int,m.groups())
  return f'.incbin "build/high_color_blobs.bin",{0 if not at else at-old_size+len(pool)},{len(pool)if not at else size}'
 assembly=re.sub(r'\.incbin "build/high_color_blobs.bin",(\d+),(\d+)',shift,assembly)
 (out/'high_color_blobs.bin').write_bytes(pool+bank[old_size:]);(out/'high_color_blobs.s').write_text(assembly)
 return len(raw)-len(packed)+old_size-len(pool)

def main():
 out=ROOT/'build';compress=compressor();saved=faces(compress)
 generator=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 database=hashlib.sha256((out/'original/RPG_RT.ldb').read_bytes()).hexdigest()
 previous=out/'battle_animation_manifest.json'
 if previous.exists():
  cached=json.loads(previous.read_text())
  if cached.get('generator_sha256')==generator and cached.get('database_sha256')==database and all((out/p).exists()and hashlib.sha256((out/p).read_bytes()).hexdigest()==h for p,h in cached.get('cached_inputs',{}).items()) and cached.get('cached_inputs'):
   print(json.dumps({'battle_animations':'cached','bank_bytes':cached['bank_bytes']}));return
 animations=array(data_root((out/'original/RPG_RT.ldb').read_bytes())[1][19]);used={}
 for aid,a in animations:
  name=filename(a.get(2,b''));ids=used.setdefault(name,set())
  for _,frame in array(a.get(12,b'')):
   for _,cell in array(frame.get(1,b'')):
    if integer(cell.get(1),1):ids.add(integer(cell.get(2),0))
 blob=bytearray();code=['/* Original Battle XYZ cells; generated, do not edit. */\nextern const u8 original_animations_start[];\n'];assets=[];sheets={};proof=[]
 def append(b,align=1):
  blob.extend(bytes((-len(blob))%align));offset=len(blob);blob.extend(b);return offset
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()}
  for name,ids in sorted(used.items()):
   if not name:continue
   path='Ruina121/game/Battle/'+name+'.xyz';raw=z.read(names[path]);w,h=struct.unpack_from('<HH',raw,4);decoded=zlib.decompress(raw[8:]);pixels=decoded[768:]
   colors=[(r>>3)|((g>>3)<<5)|((b>>3)<<10)for r,g,b in zip(decoded[:768:3],decoded[1:768:3],decoded[2:768:3])]
   palette=[0]+list(dict.fromkeys(colors[1:]));lut=bytes([0]+[palette[1:].index(c)+1 for c in colors[1:]]);pal_at=append(struct.pack('<%dH'%len(palette),*palette),2)
   mapping=[]
   for cid in sorted(ids):
    x=cid%5*96;y=cid//5*96;assert x+96<=w and y+96<=h,(name,cid,w,h)
    original=b''.join(pixels[(y+j)*w+x:(y+j)*w+x+96]for j in range(96));p=original.translate(lut)
    visible=[(i%96,i//96)for i,c in enumerate(p)if c]
    if not visible:mapping.append((cid,-1));continue
    left=max(0,min(v[0]for v in visible)-1);right=min(96,max(v[0]for v in visible)+2)
    top=max(0,min(v[1]for v in visible)-1);bottom=min(96,max(v[1]for v in visible)+2)
    cw=right-left;ch=bottom-top;data=b''.join(p[j*96+left:j*96+right]for j in range(top,bottom));bh=4096//cw;parts=[];offsets=[0]
    for start in range(0,ch,bh):
     encoded=compress(data[start*cw:(start+bh)*cw]);parts.append(encoded);offsets.append(offsets[-1]+len(encoded))
    at=append(b''.join(parts));rows_at=append(struct.pack('<%dI'%len(offsets),*offsets),4)
    n=len(assets);mapping.append((cid,n));assets.append((at,cw,ch,rows_at,pal_at,len(palette),left-48,top-48))
    # Independent transparent-mask and RGB555 equality before compression.
    restored=bytearray(9216)
    for j in range(ch):restored[(j+top)*96+left:(j+top)*96+right]=data[j*cw:(j+1)*cw]
    assert bytes(restored)==p and all((v==0)==(u==0)and(not v or palette[v]==colors[u])for v,u in zip(restored,original))
   symbol='animation_sheet_'+str(len(sheets));sheets[name]=symbol
   code.append('static const short '+symbol+'[]={'+','.join(str(v)for pair in mapping for v in pair)+'};\n')
   proof.append({'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'cells':len(ids),'RGB555_and_alpha_exact':True})
 code.append('static const AnimationCellAsset animation_cells[]={\n')
 for at,w,h,rows,pal,count,x,y in assets:
  code.append('{{original_animations_start+%d,%d,%d,(const u32*)(original_animations_start+%d),0,8,1,%d,%d,(const u16*)(original_animations_start+%d),%d},%d,%d},\n'%(at,w,h,rows,w,h,pal,count,x,y))
 code.append('};\nstatic const AnimationSheetAsset animation_sheets[]={\n')
 for aid,a in animations:
  name=filename(a.get(2,b''))
  if name in sheets:code.append('{%d,%s,sizeof(%s)/sizeof(short)/2},\n'%(aid,sheets[name],sheets[name]))
 code.append('};\n');(out/'battle_animation_assets.h').write_text(''.join(code));(out/'battle_animations.bin').write_bytes(blob)
 report={'animations':len(animations),'frames':sum(len(array(a.get(12,b'')))for _,a in animations),'sheets':len(sheets),'visible_cells':len(assets),'bank_bytes':len(blob),'lossless_storage_bytes_recovered':saved,'additional_color_quantization':False,'additional_spatial_reduction':False,'sources':proof,'bank_sha256':hashlib.sha256(blob).hexdigest()}
 report.update(generator_sha256=generator,database_sha256=database,cached_inputs={p:hashlib.sha256((out/p).read_bytes()).hexdigest()for p in ('battle_animations.bin','battle_animation_assets.h')})
 (out/'battle_animation_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='sources'},ensure_ascii=False))

if __name__=='__main__':main()
