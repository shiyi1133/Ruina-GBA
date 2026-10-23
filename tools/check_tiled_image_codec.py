"""Independent pixels, odd-size edges and mixed legacy/tiled cache ownership."""
import ctypes as C,hashlib,json,random,subprocess
import numpy as np
from project_env import ROOT
from image_codec import encode_lz4

class Image(C.Structure):
 _fields_=[('pixels',C.POINTER(C.c_ubyte)),('width',C.c_ushort),('height',C.c_ushort),('rows',C.POINTER(C.c_uint)),('palette',C.POINTER(C.c_ubyte)),('encoding',C.c_ubyte),('transparent',C.c_ubyte),('stored_width',C.c_ushort),('stored_height',C.c_ushort),('colors',C.POINTER(C.c_ushort)),('color_count',C.c_ushort)]

def main():
 target=ROOT/'build/tiled_image_codec.so'
 subprocess.run(['cc','-std=c99','-O2','-ffreestanding','-shared','-fPIC','-Iruntime/rm2k','tests/image_decoder_stub.c','platform/gba/image.c','-o',str(target)],cwd=ROOT,check=True)
 lib=C.CDLL(str(target));p=C.POINTER(C.c_ubyte);q=C.POINTER(Image)
 lib.decode_image_storage_span.argtypes=[q,C.c_int,C.c_int,C.c_int,p,C.c_uint];lib.decode_image_row.argtypes=[q,C.c_int,p,C.c_uint]
 lib.image_storage_tile.argtypes=[q,C.c_int,C.c_int];lib.image_storage_tile.restype=p
 lib.image_decode_scratch.restype=C.c_void_p
 rng=np.random.default_rng(0x524742);records=[];rows=spans=whole_tiles=0
 for w,h in[(1,1),(7,9),(33,41),(240,160),(321,241),(1023,17)]:
  pixels=rng.integers(0,256,(h,w),dtype=np.uint8);pixels[:h//2,:w//2]=rng.integers(0,3,(h//2,w//2),dtype=np.uint8)
  pool=bytearray();refs=[]
  for y in range(0,h,8):
   for x in range(0,w,8):
    tile=np.zeros((8,8),np.uint8);a=pixels[y:y+8,x:x+8];tile[:a.shape[0],:a.shape[1]]=a;raw=tile.tobytes();compressed=encode_lz4(raw)
    size=len(compressed)if len(compressed)<64 else 0;refs.append(len(pool)|(size<<24));pool.extend(compressed if size else raw)
  data=(C.c_ubyte*len(pool)).from_buffer_copy(pool);table=(C.c_uint*len(refs))(*refs);im=Image(data,w,h,table,None,6,0,w,h,None);row=(C.c_ubyte*1024)()
  # A legacy block uses the very same 4096-byte workspace; alternate it with
  # native tiles to prove that neither cache can reuse overwritten bytes.
  old_pixels=rng.integers(0,16,(32,64),dtype=np.uint8);packed=((old_pixels[:,::2]<<4)|old_pixels[:,1::2]).tobytes();old=encode_lz4(packed)
  olddata=(C.c_ubyte*len(old)).from_buffer_copy(old);oldrows=(C.c_uint*2)(0,len(old));oldpal=(C.c_ubyte*16)(*range(16));legacy=Image(olddata,64,32,oldrows,oldpal,4,1,64,32,None)
  for y in range(h):
   assert lib.decode_image_row(C.byref(im),y,row,1024)==w
   assert bytes(row[:w])==pixels[y].tobytes(),(w,h,y,'row');rows+=1
   if y%3==0:
    assert lib.decode_image_row(C.byref(legacy),y%32,row,1024)==64
    assert bytes(row[:64])==old_pixels[y%32].tobytes()
    C.memset(lib.image_decode_scratch(),0xa5,4096)
    assert lib.decode_image_row(C.byref(legacy),y%32,row,1024)==64 and bytes(row[:64])==old_pixels[y%32].tobytes()
   for _ in range(3):
    x=int(rng.integers(0,w));length=int(rng.integers(1,w-x+1))
    assert lib.decode_image_storage_span(C.byref(im),y,x,length,row,1024)==length
    assert bytes(row[:length])==pixels[y,x:x+length].tobytes(),(w,h,y,x,length,'span');spans+=1
  for y,x,length,cap in[(-1,0,1,1024),(h,0,1,1024),(0,-1,1,1024),(0,w,1,1024),(0,0,w+1,1024),(0,0,1,0)]:
   assert not lib.decode_image_storage_span(C.byref(im),y,x,length,row,cap),(w,h,y,x,length,cap)
  # The fast native compositor borrows one complete tile, then copies it
  # before any other decoder call. Include padded odd edges and cache
  # invalidation by legacy blocks and the shared workspace borrower.
  for ty in range((h+7)//8):
   for tx in range((w+7)//8):
    for invalidation in range(3):
     if invalidation==1:
      assert lib.decode_image_row(C.byref(legacy),ty%32,row,1024)==64
     elif invalidation==2:C.memset(lib.image_decode_scratch(),0xa5,4096)
     tile=lib.image_storage_tile(C.byref(im),tx,ty);assert tile
     expected=np.zeros((8,8),np.uint8);area=pixels[ty*8:ty*8+8,tx*8:tx*8+8];expected[:area.shape[0],:area.shape[1]]=area
     assert bytes(tile[:64])==expected.tobytes(),(w,h,tx,ty,invalidation,'whole tile');whole_tiles+=1
  for tx,ty in[(-1,0),(0,-1),((w+7)//8,0),(0,(h+7)//8)]:
   assert not lib.image_storage_tile(C.byref(im),tx,ty)
  assert not lib.image_storage_tile(C.byref(legacy),0,0)
  records.append({'width':w,'height':h,'tiles':len(refs),'compressed_bytes':len(pool)})
 cached_tile=im
 # Constant storage preserves a nonzero local index and transparency meaning;
 # it is not equivalent to rewriting every color as palette index zero.
 for value in(0,1,17,255):
  data=(C.c_ubyte*1)(value);im=Image(data,641,479,None,None,7,1,641,479,None);row=(C.c_ubyte*1024)()
  for y in(0,17,478):
   assert lib.decode_image_row(C.byref(im),y,row,1024)==641 and bytes(row[:641])==bytes([value])*641;rows+=1
   assert lib.decode_image_storage_span(C.byref(im),y,53,187,row,1024)==187 and bytes(row[:187])==bytes([value])*187;spans+=1
 # Full-index block storage is also used by every battle animation cell.
 # Alternate it with tiles, legacy nibble blocks and scratch borrowers to
 # exercise the optimized clipped-span path with real cache invalidations.
 block_spans=0
 for w,h in [(1,23),(7,99),(33,129),(96,96),(321,41),(1023,17)]:
  source=rng.integers(0,256,(h,w),dtype=np.uint8);source[:h//2,:w//2]%=3
  bh=4096//w;pool=bytearray();offsets=[0]
  for y in range(0,h,bh):pool.extend(encode_lz4(source[y:y+bh].tobytes()));offsets.append(len(pool))
  data=(C.c_ubyte*len(pool)).from_buffer_copy(pool);table=(C.c_uint*len(offsets))(*offsets);block=Image(data,w,h,table,None,8,1,w,h,None)
  for y in range(h):
   for invalidation in range(4):
    if invalidation==1:assert lib.decode_image_row(C.byref(legacy),y%32,row,1024)==64
    elif invalidation==2:assert lib.image_storage_tile(C.byref(cached_tile),0,0)
    elif invalidation==3:C.memset(lib.image_decode_scratch(),0xa5,4096)
    x=int(rng.integers(0,w));length=int(rng.integers(1,w-x+1));assert lib.decode_image_storage_span(C.byref(block),y,x,length,row,1024)==length
    assert bytes(row[:length])==source[y,x:x+length].tobytes(),(w,h,y,x,length,invalidation,'block span');block_spans+=1
   assert lib.decode_image_row(C.byref(block),y,row,1024)==w and bytes(row[:w])==source[y].tobytes();rows+=1
  for y,x,length,cap in [(-1,0,1,1024),(h,0,1,1024),(0,-1,1,1024),(0,w,1,1024),(0,0,w+1,1024),(0,0,1,0)]:assert not lib.decode_image_storage_span(C.byref(block),y,x,length,row,cap)
 report={'status':'pass','kind':'independent random source pixels; decoder cache interleaving and odd-size image edges','rows':rows,'spans':spans,'whole_tile_borrows':whole_tiles,'block_indexed_spans':block_spans,'cases':records,
         'sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in['platform/gba/image.c','runtime/rm2k/types.h','tests/image_decoder_stub.c']}}
 out=ROOT/'evidence/optimization_20261022/art';out.mkdir(parents=True,exist_ok=True);(out/'tiled_codec_host.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
