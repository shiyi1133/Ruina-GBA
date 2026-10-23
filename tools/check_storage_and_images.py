"""Independent decoded-pixel checks and exact packed-state round trips.
Host storage checks are separate from emulator save/cold-load acceptance.
"""
import ctypes as C,hashlib,json,random,subprocess
from project_env import ROOT
from save_observation import save_payload
from PIL import Image as PillowImage

class Image(C.Structure):
 _fields_=[('pixels',C.POINTER(C.c_ubyte)),('width',C.c_ushort),('height',C.c_ushort),('rows',C.POINTER(C.c_uint)),('palette',C.POINTER(C.c_ubyte)),('encoding',C.c_ubyte),('transparent',C.c_ubyte),('stored_width',C.c_ushort),('stored_height',C.c_ushort),('colors',C.POINTER(C.c_ushort)),('color_count',C.c_ushort)]

def main():
 sources=['platform/gba/image.c','runtime/rm2k/storage_codec.c','tests/state_size.c','build/assets.c'];target=ROOT/'build/storage_images_host.so'
 if (ROOT/'build/high_color_blobs.s').exists():sources.append('build/high_color_blobs.s')
 subprocess.run(['cc','-std=c99','-O2','-fPIC','-shared','-Iruntime/rm2k','-Isource',*sources,'-o',str(target)],cwd=ROOT,check=True)
 lib=C.CDLL(str(target));lib.decode_image_row.argtypes=[C.POINTER(Image),C.c_int,C.POINTER(C.c_ubyte),C.c_uint]
 lib.decode_image_storage_span.argtypes=[C.POINTER(Image),C.c_int,C.c_int,C.c_int,C.POINTER(C.c_ubyte),C.c_uint]
 lib.pack_state.argtypes=[C.POINTER(C.c_ubyte),C.c_uint,C.POINTER(C.c_ubyte),C.c_uint];lib.unpack_state.argtypes=lib.pack_state.argtypes
 manifest=json.loads((ROOT/'build/asset_manifest.json').read_text());images=(Image*len(manifest['images'])).in_dll(lib,'images');rows=spans=0;rng=random.Random(0x5255494e)
 for i,meta in enumerate(manifest['image_storage']):
  im=images[i];original=PillowImage.open(ROOT/'build'/(meta['image']+'_palette.png'));pixels=original.tobytes();w,h=original.size
  assert (im.width,im.height)==(meta['width'],meta['height']);buffer=(C.c_ubyte*im.width)()
  yy=sorted({0,im.height-1,im.height//2,7,8,15,16}|{rng.randrange(im.height)for _ in range(4)})
  for y in yy:
   if y>=im.height:continue
   assert lib.decode_image_row(C.byref(im),y,buffer,len(buffer))==im.width
   expected=bytes(pixels[(y*h//im.height)*w+x*w//im.width]for x in range(im.width));assert bytes(buffer)==expected,(meta['image'],y)
   rows+=1
  assert lib.decode_image_row(C.byref(im),-1,buffer,len(buffer))==0
  assert lib.decode_image_row(C.byref(im),im.height,buffer,len(buffer))==0
  assert lib.decode_image_row(C.byref(im),0,buffer,im.width-1)==0
  # Compare stored spans against the independently saved indexed PNG, including
  # odd nibble offsets, short dirty regions and eight-line block boundaries.
  small=(C.c_ubyte*32)()
  for y in sorted({0,h-1,h//2,7,8,15,16}):
   if y>=h:continue
   for x in sorted({0,1,w//2,max(0,w-19),w-1}):
    if x>=w:continue
    length=min(19,w-x)
    assert lib.decode_image_storage_span(C.byref(im),y,x,length,small,len(small))==length
    assert bytes(small[:length])==pixels[y*w+x:y*w+x+length],(meta['image'],y,x)
    spans+=1
  assert not lib.decode_image_storage_span(C.byref(im),0,-1,1,small,len(small))
  assert not lib.decode_image_storage_span(C.byref(im),0,w-1,2,small,len(small))
  assert not lib.decode_image_storage_span(C.byref(im),h,0,1,small,len(small))
  assert not lib.decode_image_storage_span(C.byref(im),0,0,min(w,19),small,0)
 n=lib.proof_game_size();assert lib.proof_extension_offset()==32068
 cases=[b'\0'*n,b'\xff'*n,bytes(range(256))*200,bytes(rng.randrange(256)for _ in range(n))]
 for p in sorted((ROOT/'history').glob('legacy_*_v2.sav')):cases.append(save_payload(p.read_bytes())[1])
 saved=ROOT/'history/pre_full_features_20261021/废都物语_GBA_开篇开发验证版.gba'
 proof=[]
 for value in cases:
  source=(C.c_ubyte*len(value)).from_buffer_copy(value);packed=(C.c_ubyte*(len(value)*2+128))();result=lib.pack_state(source,len(value),packed,len(packed));assert result>0
  output=(C.c_ubyte*len(value))();assert lib.unpack_state(packed,result,output,len(output));assert bytes(output)==value
  assert not lib.unpack_state(packed,result,output,len(output)-1)
  if result>1:assert not lib.unpack_state(packed,result-1,output,len(output))
  tiny=(C.c_ubyte*1)();assert not lib.pack_state(source,len(value),tiny,1)
  proof.append({'raw_bytes':len(value),'packed_bytes':result,'fits_SRAM':result+28+32*20<=32768})
 r={'status':'pass','kind':'host decoded-image comparison and exact state-storage checks','images':len(images),'image_rows_checked':rows,'image_spans_checked':spans,'resources':len(manifest['resources']),'encoded_image_bytes':manifest['encoded_image_bytes'],'current_game_bytes':n,'legacy_v4_prefix_bytes':32068,'state_cases':proof,'incompressible_state':'fails bounded capacity; does not silently truncate','emulator_gameplay':'separate spot checks required','sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in sources+(['build/high_color_blobs.bin']if(ROOT/'build/high_color_blobs.bin').exists()else[])}}
 out=ROOT/'evidence/full_features';out.mkdir(exist_ok=True);(out/'storage_images_host.json').write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps(r,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
