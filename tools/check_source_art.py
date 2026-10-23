"""Compare native decoded art with the user's untouched indexed XYZ sources.
Palette budgets are measured separately from storage fidelity. No preview PNG
is treated as the original source of truth.
"""
import ctypes as C,hashlib,json,struct,subprocess,zipfile,zlib
import numpy as np
from project_env import ROOT,ARCHIVE
from portrait_assets import logical
from check_storage_and_images import Image
class Scene(C.Structure):
 _fields_=[('colors',C.POINTER(C.c_ushort)),('nearest',C.POINTER(C.c_ubyte)),('source_remap',C.POINTER(C.c_ubyte)),('bits',C.c_uint),('sorted_colors',C.POINTER(C.c_ushort)),('sorted_indices',C.POINTER(C.c_ubyte))]
def main():
 sources=['platform/gba/image.c','build/assets.c','build/high_color_blobs.s'];target=ROOT/'build/source_art_host.so'
 subprocess.run(['cc','-std=c99','-O2','-ffreestanding','-fPIC','-shared','-Iruntime/rm2k','-Isource',*sources,'-o',str(target)],cwd=ROOT,check=True)
 lib=C.CDLL(str(target));m=json.loads((ROOT/'build/asset_manifest.json').read_text());images=(Image*len(m['images'])).in_dll(lib,'images');n=C.c_uint.in_dll(lib,'image_scene_count').value;scenes=(Scene*n).in_dll(lib,'image_scenes');lib.decode_image_row.argtypes=[C.POINTER(Image),C.c_int,C.POINTER(C.c_ubyte),C.c_uint];rows=[]
 def namehash(value):
  h=2166136261
  for b in value:h=((h^b)*16777619)&0xffffffff
  return h
 folders=['Picture','Panorama','ChipSet','CharSet','Backdrop']
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(p):p for p in z.namelist()};lookup={}
  for p in names:
   if not p.endswith('.xyz'):continue
   for kind,folder in enumerate(folders):
    if '/'+folder+'/'in p:lookup[kind,namehash(p.rsplit('/',1)[1][:-4].encode('cp932'))]=p
  for r in m['resources']:
   i=r['image'];im=images[i];path=lookup[r['kind'],r['hash']];raw=z.read(names[path]);w,h=struct.unpack_from('<HH',raw,4);payload=zlib.decompress(raw[8:]);idx=np.frombuffer(payload,np.uint8,offset=768).reshape(h,w);rgb=np.frombuffer(payload,np.uint8,768).reshape(256,3).astype(np.uint16)>>3;pal=rgb[:,0]|(rgb[:,1]<<5)|(rgb[:,2]<<10);mask=idx!=0 if r['kind']in(0,2,3)else np.ones_like(idx,dtype=bool)
   assert (im.width,im.height)==(w,h),(path,(im.width,im.height),(w,h))
   decoded=np.empty((h,w),np.uint8);buf=(C.c_ubyte*w)()
   for y in range(h):assert lib.decode_image_row(C.byref(im),y,buf,w)==w;decoded[y]=buf[:]
   colors=np.ctypeslib.as_array(im.colors,shape=(im.color_count or 256,));local=colors[decoded];original=pal[idx];different=int(np.count_nonzero((local!=original)&mask));alpha=int(np.count_nonzero((decoded==0)!=(idx==0)))if r['kind']in(0,2,3)else 0
   scene=scenes[i];fit=np.ctypeslib.as_array(scene.colors,shape=(256,))[np.ctypeslib.as_array(scene.source_remap,shape=(256,))[decoded]];delta=np.stack(((fit&31).astype(int)-(original&31),((fit>>5)&31).astype(int)-((original>>5)&31),((fit>>10)&31).astype(int)-(original>>10)),axis=2);squared=np.sum(delta*delta,axis=2)[mask]
   row={'source':path,'kind':folders[r['kind']],'image':i,'pixels':int(mask.sum()),'stored_RGB555_different_pixels':different,'alpha_different_pixels':alpha,'display_with_own_scene_different_pixels':int(np.count_nonzero((fit!=original)&mask)),'display_RGB555_mean_squared_error':float(squared.mean())if len(squared)else 0,'display_RGB555_max_squared_error':int(squared.max())if len(squared)else 0,'fallback_16_color_OBJ_atlas':r['kind']==3};rows.append(row)
   if r['kind']!=3:assert not different and not alpha,row
 result={'status':'pass','scope':'all native Picture/Panorama/ChipSet/Backdrop storage versus original XYZ, RGB555 and alpha; CharSet fallback reduction reported separately, native actor bank tested separately','resources':len(rows),'native_non_charset_pixels':sum(r['pixels']for r in rows if r['kind']!='CharSet'),'native_non_charset_storage_differences':sum(r['stored_RGB555_different_pixels']for r in rows if r['kind']!='CharSet'),'own_scene_palette_fitted_resources':sum(bool(r['display_with_own_scene_different_pixels'])for r in rows if r['kind']!='CharSet'),'archive_sha256':m['archive_sha256'],'bank_sha256':hashlib.sha256((ROOT/'build/high_color_blobs.bin').read_bytes()).hexdigest(),'rows':rows}
 out=ROOT/'evidence/optimization_20261022/source_art';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'},ensure_ascii=False,indent=2));print('own palette approximations:',json.dumps([r for r in rows if r['kind']!='CharSet'and r['display_with_own_scene_different_pixels']],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
