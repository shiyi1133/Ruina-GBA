"""Verify GBA pixels against independent RGB-channel alpha calculations."""
import hashlib,json,re
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture

def main():
 source=(ROOT/'build/assets.c').read_text();m=re.search(r'game_palette\[256\]\s*=\s*\{([^}]+)\}',source)
 palette=np.array([int(x)for x in m.group(1).split(',')if x.strip()],dtype=np.int32)
 colors=np.stack([palette&31,(palette>>5)&31,(palette>>10)&31],axis=1)
 manifest=json.loads((ROOT/'build/asset_manifest.json').read_text());metadata={x['image']:x for x in manifest['image_storage']}
 grid=np.arange(256,dtype=np.int32).reshape(16,16).repeat(10,axis=0).repeat(15,axis=1)
 def nearest(rgb):
  flat=rgb.reshape(-1,3);unique,inverse=np.unique(flat,axis=0,return_inverse=True)
  distance=((unique[:,None,:]-colors[None,:,:])**2).sum(axis=2)
  return distance.argmin(axis=1)[inverse].reshape(rgb.shape[:-1])
 def expected(alpha,image,tone):
  if alpha<0 or alpha>=100:return colors[grid]
  name=manifest['images'][image];meta=metadata[name];preview=Image.open(ROOT/'build'/(name+'_palette.png'));raw=np.array(preview,dtype=np.int32);local=np.array(preview.getpalette(),dtype=np.int32).reshape(256,3)>>3
  height,width=raw.shape;x=(np.arange(240)*meta['width']//240)*width//meta['width'];y=(np.arange(160)*meta['height']//160)*height//meta['height']
  sampled=raw[y[:,None],x[None,:]];rgb=local[sampled]
  if tone:
   gray=(rgb[:,:,0]*30+rgb[:,:,1]*59+rgb[:,:,2]*11)//100
   desaturated=gray[:,:,None]+np.trunc((rgb-gray[:,:,None])*tone[3]/100).astype(np.int32)
   toned=np.clip(desaturated*np.array(tone[:3])//100,0,31);rgb=toned
  a=alpha*32//100;blended=(rgb*(32-a)+colors[grid]*a)//32
  out=colors[nearest(blended)];out[sampled==0]=colors[grid][sampled==0]
  return out
 rom,elf,digest=fixture('tests/uniform_alpha_gba.c','uniform_alpha')
 out=ROOT/'evidence/full_features/uniform_alpha'/hashlib.sha256(rom.read_bytes()).hexdigest()[:12];out.mkdir(parents=True,exist_ok=True)
 e=Emulator(rom=rom,elf=elf);differences=[]
 try:
  for stage,(alpha,image,tone)in enumerate([(-1,446,None),(70,446,None),(25,446,None),(0,446,None),(100,446,None),(70,5,[80,110,90,50])],1):
   for _ in range(1000):
    if e.debug()[14]==stage:break
    e.frames(10)
   else:raise AssertionError(('stage',stage,e.debug()))
   e.frames(2);p=out/(str(stage)+'.png');e.shot(p);actual=np.array(Image.open(p).convert('RGB'))>>3
   differences.append(int(np.any(actual!=expected(alpha,image,tone),axis=2).sum()))
   e.frames(2,1);e.frames(2)
  result={'status':'pass'if not any(differences)else 'fail','kind':'actual GBA pixels over 256 destination palette colors, independent channel alpha/tint arithmetic, original converted source pixels','cases':['opaque background','70 percent transparency','25 percent transparency','opaque source','fully transparent source','colored source plus tint and alpha'],'different_pixels':differences,'production_rom_sha256':digest,'fixture_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'alpha_precision':'33 blend weights, nearest RGB555 palette color; no spatial dither','commands':e.log,'hardware':'not_run'}
  (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'latest_attempt.json').write_text(json.dumps({'status':result['status'],'report':str((out/'result.json').relative_to(ROOT))},ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='commands'},ensure_ascii=False,indent=2));assert result['status']=='pass',differences
 finally:e.close()

if __name__=='__main__':main()
