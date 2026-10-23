"""Native-size local RGB555 art and small independently decoded 8x8 tiles.

The old converter reduced a whole image to 15/16 colors, then mapped those to
one global palette. Here source colors survive independently of the currently
displayed scene. Each scene keeps the 16 UI colors and up to 240 art colors.
Map palettes get a full RGB555 lookup; other scenes use a compact RGB444 lookup.
"""
import ctypes as C,ctypes.util,hashlib,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from image_codec import encode_lz4

def cbytes(name,data,ctype='unsigned char'):
 return f'const {ctype} {name}[{len(data)}]={{'+','.join(str(int(v))for v in data)+'};\n'

def rgb555(a):
 a=np.asarray(a,dtype=np.uint16);return(a[...,0]>>3)|((a[...,1]>>3)<<5)|((a[...,2]>>3)<<10)

def rgb8(colors):
 c=np.asarray(colors,dtype=np.uint16);return np.column_stack(((c&31)*255//31,((c>>5)&31)*255//31,((c>>10)&31)*255//31)).astype(np.uint8)

def nearest(query,colors):
 q=np.asarray(query,dtype=np.int32);p=np.asarray(colors,dtype=np.int32)
 qv=np.column_stack((q&31,(q>>5)&31,(q>>10)&31));pv=np.column_stack((p&31,(p>>5)&31,(p>>10)&31))
 best=np.full(len(q),100000,np.int32);indices=np.zeros(len(q),np.uint8)
 for i,color in enumerate(pv):
  d=qv-color;dist=np.einsum('ij,ij->i',d,d);mask=dist<best;best[mask]=dist[mask];indices[mask]=i
 return indices

def scene_colors(source,counts,ui):
 candidates=list(dict.fromkeys(int(c)for c in source if c not in set(ui)));weights=np.asarray([max(1,int(counts.get(c,1)))for c in candidates],dtype=float)
 v=np.asarray([[c&31,(c>>5)&31,(c>>10)&31]for c in candidates],dtype=float)
 fixed=np.asarray([[c&31,(c>>5)&31,(c>>10)&31]for c in ui],dtype=float)
 while len(v)>240:
  d=v[:,None,:]-v[None,:,:];cost=np.einsum('ijk,ijk->ij',d,d)*weights[:,None]*weights[None,:]/(weights[:,None]+weights[None,:]);np.fill_diagonal(cost,np.inf)
  df=v[:,None,:]-fixed[None,:,:];cf=np.einsum('ijk,ijk->ij',df,df)*weights[:,None]
  a,b=np.unravel_index(np.argmin(cost),cost.shape);x,y=np.unravel_index(np.argmin(cf),cf.shape)
  if cf[x,y]<=cost[a,b]:v=np.delete(v,x,0);weights=np.delete(weights,x)
  else:
   v[a]=(v[a]*weights[a]+v[b]*weights[b])/(weights[a]+weights[b]);weights[a]+=weights[b];v=np.delete(v,b,0);weights=np.delete(weights,b)
 if len(v):
  v=np.clip(np.rint(v),0,31).astype(np.uint16);extra=(v[:,0]|(v[:,1]<<5)|(v[:,2]<<10)).tolist()
 else:extra=[]
 result=list(ui)+extra;return result+[ui[14]]*(256-len(result))

def convert_images(imgs,labels,resources,out,global_palette):
 arrays=[];infos=[];storage=[];details=[];pool=bytearray();tile_pool={};palette_cache={};scene_cache={};scene_infos=[];binary_arrays=[]
 ordinary=len(imgs);native={i for kind,_,i in resources if kind in(1,2,3)};charsets={i for kind,_,i in resources if kind==3}
 backgrounds={i for kind,_,i in resources if kind==1}
 ui=rgb555(np.asarray(global_palette[:48],np.uint8).reshape(16,3)).tolist()
 compressed=None
 try:
  library=C.CDLL(ctypes.util.find_library('lz4'));compress=library.LZ4_compress_HC;compress.argtypes=[C.c_void_p,C.c_void_p,C.c_int,C.c_int,C.c_int];compress.restype=C.c_int
  def compressed(data):
   src=C.create_string_buffer(data);dst=C.create_string_buffer(len(data)+128);n=compress(src,dst,len(data),len(dst),12);return dst.raw[:n]if n else data
 except(OSError,AttributeError,TypeError):compressed=encode_lz4
 def color_array(colors):
  key=struct.pack('<%dH'%len(colors),*colors)
  if key not in palette_cache:
   name='color_palette_'+str(len(palette_cache));palette_cache[key]=name;arrays.append(cbytes(name,colors,'unsigned short'))
  return palette_cache[key]
 def tile_reference(data):
  if data not in tile_pool:
   enc=compressed(data);size=len(enc)
   if size>=64:enc=data;size=0
   assert len(pool)<1<<24 and size<256
   tile_pool[data]=len(pool)|(size<<24);pool.extend(enc)
  return tile_pool[data]
 def image_scene(index,name,colors,pixels,count):
  counts=dict(zip(*np.unique(pixels,return_counts=True)));weights={int(colors[k]):int(v)for k,v in counts.items()}
  pal=scene_colors(colors[:count],weights,ui);bits=15 if index in native and index not in charsets else 12
  key=(tuple(pal),bits)
  if key not in scene_cache:
   number=len(scene_cache);ps=color_array(pal);lookup='scene_nearest_'+str(number);sc='scene_sorted_'+str(number);si='scene_indices_'+str(number)
   if bits==15:q=np.arange(32768,dtype=np.uint16)
   else:
    n=np.arange(4096,dtype=np.uint16);q=((n&15)*2+1)|((((n>>4)&15)*2+1)<<5)|((((n>>8)&15)*2+1)<<10)
   table=nearest(q,pal);arrays.append(f'extern const unsigned char {lookup}[];\n');binary_arrays.append((lookup,table.tobytes()));order=np.argsort(pal,kind='stable');arrays.append(cbytes(sc,np.asarray(pal)[order],'unsigned short'));arrays.append(cbytes(si,order));scene_cache[key]=(ps,lookup,sc,si)
  ps,lookup,sc,si=scene_cache[key];own=nearest(colors[:count],pal);own=np.pad(own,(0,256-len(own)))
  own_name='scene_source_'+name;arrays.append(cbytes(own_name,own));scene_infos.append('{'+','.join((ps,lookup,own_name,str(bits),sc,si))+'}')
 for index,(name,im)in enumerate(zip(labels,imgs)):
  width,height=im.size;rgba=im.mode=='RGBA';a=np.asarray(im.convert('RGB'));packed=rgb555(a);alpha=np.asarray(im.getchannel('A'))<128 if rgba else np.zeros((height,width),bool)
  obj_compat=index in charsets
  visible=packed[~alpha]if rgba else packed.ravel();unique=np.unique(visible);transparent=int(packed[alpha][0])if rgba and np.any(alpha)else 0
  limit=15 if rgba else 16
  if obj_compat and len(unique)>limit:
   sample=Image.fromarray(a.reshape(-1,3)[(~alpha).ravel()].reshape(1,-1,3),'RGB').quantize(colors=limit,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
   local=rgb555(np.asarray(sample.getpalette(),np.uint8).reshape(-1,3)[:limit]).tolist()
  else:local=[int(c)for c in unique]
  colors=([transparent]+local)if rgba else local
  colors=colors+[0]*((16 if obj_compat else 256)-len(colors));count=len(local)+int(rgba)
  # Source palettes contain at most 256 colors; adapted illustrations can
  # contain more and receive their own 256-color reduction, never 16 colors.
  if not obj_compat and count>256:
   limit=255 if rgba else 256;q=Image.fromarray(a,'RGB').quantize(colors=limit,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
   local=rgb555(np.asarray(q.getpalette(),np.uint8).reshape(-1,3)[:limit]).tolist();colors=([transparent]+local)if rgba else local;count=len(colors);colors+=([0]*(256-count))
  mapping=nearest(np.unique(packed),colors[:count]);all_colors=np.unique(packed);lut=np.zeros(32768,np.uint8);lut[all_colors]=mapping
  pixels=lut[packed]
  if rgba:
   # A visible pixel sharing the transparent color still needs a nonzero code.
   visible_map=nearest(all_colors,colors[1:count])+1;lut[all_colors]=visible_map;pixels=lut[packed];pixels[alpha]=0
  scene_indices=False
  if index in backgrounds and not rgba and len(set(colors[:count])-set(ui))<=240:
   # Exact RGB555 recoloring of indices, not quantization: every source color
   # fits beside the 16 UI colors. Stored pixels can then copy directly into
   # their own scene without another palette lookup for every visible pixel.
   counts=dict(zip(*np.unique(pixels,return_counts=True)));weights={int(colors[k]):int(v)for k,v in counts.items()}
   own=scene_colors(colors[:count],weights,ui);mapping=nearest(colors[:count],own);pixels=mapping[pixels];colors=own;count=256;scene_indices=True
  symbol=color_array(colors);before=len(pool)
  if np.all(pixels==pixels[0,0]):
   arrays.append(cbytes('img_'+name,[int(pixels[0,0])]))
   infos.append(f'{{img_{name},{width},{height},0,0,7,{int(rgba)},{width},{height},{symbol},{count}}}')
   encoded_bytes=1;encoding=7
  elif obj_compat:
   stride=(width+1)//2;padded=np.pad(pixels,((0,0),(0,width&1)));raw=((padded[:,::2]<<4)|padded[:,1::2]).tobytes();bh=4096//stride;blob=bytearray();offsets=[0]
   for y in range(0,height,bh):blob.extend(compressed(raw[y*stride:(y+bh)*stride]));offsets.append(len(blob))
   arrays.append(cbytes('img_'+name,blob));arrays.append(cbytes('rows_'+name,offsets,'unsigned int'));arrays.append(cbytes('local_'+name,range(16)))
   infos.append(f'{{img_{name},{width},{height},rows_{name},local_{name},4,{int(rgba)},{width},{height},{symbol},{count}}}')
   encoded_bytes=len(blob)+len(offsets)*4;encoding=4
  else:
   refs=[]
   for y in range(0,height,8):
    for x in range(0,width,8):
     tile=np.zeros((8,8),np.uint8);part=pixels[y:y+8,x:x+8];tile[:part.shape[0],:part.shape[1]]=part;refs.append(tile_reference(tile.tobytes()))
   arrays.append(cbytes('rows_'+name,refs,'unsigned int'));infos.append(f'{{high_color_tiles,{width},{height},rows_{name},0,6,{int(rgba)},{width},{height},{symbol},{count}}}')
   encoded_bytes=len(pool)-before+len(refs)*4;encoding=6
  preview=Image.fromarray(pixels,'P');p=rgb8(colors);preview.putpalette(p.ravel().tolist()+[0]*(768-p.size));preview.save(out/(name+'_palette.png'))
  image_scene(index,name,colors,pixels,count)
  storage.append({'image':name,'width':width,'height':height,'stored_width':width,'stored_height':height,'encoding':encoding,'bytes':encoded_bytes,'pixels':width*height,'RGB555_local_colors':count,'original_visible_RGB555_colors':len(unique),'native_scene_indices':scene_indices,'OBJ_compatibility_reduction':obj_compat,'additional_spatial_reduction':False})
  details.append((pixels,colors,symbol))
 # Every atlas quadrant retains its original local color indices. The same
 # atlas palette/remap is shared across all quadrants; no global 16-color pass.
 chip_ids=[];chip_quads=[];quad_cache={}
 for kind,hash_value,image_id in resources:
  if kind!=2:continue
  pixels,colors,symbol=details[image_id];ids=[]
  for y in range(0,256,8):
   for x in range(0,480,8):
    data=pixels[y:y+8,x:x+8].tobytes();key=(symbol,data)
    if key not in quad_cache:
     name='chipquad'+str(len(quad_cache));idx=len(labels);quad_cache[key]=idx;labels.append(name);arrays.append(cbytes('img_'+name,data))
     flags=129 if not any(data)else 1;infos.append(f'{{img_{name},8,8,0,0,0,{flags},8,8,{symbol},256}}')
     preview=Image.frombytes('P',(8,8),data);preview.putpalette(rgb8(colors).ravel().tolist());preview.save(out/(name+'_palette.png'))
     storage.append({'image':name,'width':8,'height':8,'stored_width':8,'stored_height':8,'encoding':0,'bytes':64,'pixels':64,'RGB555_local_colors':256,'additional_spatial_reduction':False})
    ids.append(quad_cache[key])
  chip_ids.append(image_id);chip_quads.append(ids)
 arrays.insert(0,'extern const unsigned char high_color_tiles[];\n');binary_arrays.insert(0,('high_color_tiles',bytes(pool)))
 binary=bytearray();assembly=['.section .rodata.high_color,"a",%progbits']
 for name,data in binary_arrays:
  assembly.extend(['.balign 4','.global '+name,name+':',f'.incbin "build/high_color_blobs.bin",{len(binary)},{len(data)}']);binary.extend(data)
 (out/'high_color_blobs.bin').write_bytes(binary);(out/'high_color_blobs.s').write_text('\n'.join(assembly)+'\n')
 arrays.append(cbytes('chip_image_ids',chip_ids,'short'));arrays.append('const unsigned short chip_quad_image_ids[][1920]={'+','.join('{'+','.join(str(x)for x in row)+'}'for row in chip_quads)+'};\n');arrays.append('const unsigned chip_image_count='+str(len(chip_ids))+';\n')
 arrays.append('const ScenePalette image_scenes[]={'+','.join(scene_infos)+'};\n');arrays.append('const unsigned image_scene_count='+str(ordinary)+';\n')
 manifest={'format':'local RGB555 palettes; independently compressed 8x8 8bpp tiles; native image dimensions',
           'ordinary_images':ordinary,'unique_compressed_tiles':len(tile_pool),'tile_pool_bytes':len(pool),'scene_palette_variants':len(scene_cache),
           'scene_lookup_bytes':sum((32768 if bits==15 else 4096)for(_,bits)in scene_cache),'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
 (out/'high_color_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps(manifest,ensure_ascii=False,indent=2),flush=True)
 return arrays,infos,storage
