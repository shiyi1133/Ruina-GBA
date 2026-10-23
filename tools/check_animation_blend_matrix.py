"""Independent real-LCD proof of every percentage and lookup-workspace reuse."""
import hashlib,json,re
import numpy as np
from PIL import Image
from project_env import ROOT
from drive_opening import Emulator
from gba_fixture import fixture

def main():
 rng=np.random.default_rng(0x414c5048);pixels=rng.integers(0,16,(5,7),dtype=np.uint8);colors=rng.integers(0,32768,16,dtype=np.uint16)
 (ROOT/'build/animation_blend_matrix.h').write_text('static const u8 blend_pixels[35]={'+','.join(map(str,pixels.ravel()))+'};\nstatic const u16 blend_colors[16]={'+','.join(map(str,colors))+'};\nstatic const Image blend_source={blend_pixels,7,5,0,0,0,1,7,5,blend_colors,16};\n')
 rom,elf,digest=fixture('tests/animation_blend_matrix_gba.c','animation_blend_matrix');out=ROOT/'evidence/animation_optimization_20261023'/('blend_'+digest[:12]);out.mkdir(parents=True,exist_ok=True)
 palette=np.array([int(v)for v in re.search(r'game_palette\[256\]\s*=\s*\{([^}]+)\}',(ROOT/'build/assets.c').read_text()).group(1).split(',')],dtype=np.int64)
 def channels(c):return np.stack((c&31,c>>5&31,c>>10&31),axis=-1).astype(np.int64)
 base=channels(palette[11]);source=channels(colors);tone=np.array([80,110,90,50]);gray=(source[:,0]*30+source[:,1]*59+source[:,2]*11)//100;toned=np.clip(np.trunc((gray[:,None]+np.trunc((source-gray[:,None])*tone[3]/100))*tone[:3]/100).astype(np.int64),0,31)
 def cell(screen,x,y,w,h,opacity,tint):
  l=max(x,0);r=min(x+w,240);t=max(y,0);b=min(y+h,160);xx=(np.arange(l,r)-x)*7//w;yy=(np.arange(t,b)-y)*5//h;index=pixels[yy[:,None],xx[None,:]];old=screen[t:b,l:r];alpha=(100-opacity)*256//100;rgb=(toned if tint else source)[index];result=(rgb*alpha+old*(256-alpha)+128)>>8;old[index!=0]=result[index!=0]
 e=Emulator(rom=rom,elf=elf);rows=[]
 try:
  for stage in range(3):
   for _ in range(1000):
    if e.debug()[14]==stage+1:break
    e.frames(2)
   else:raise AssertionError(('blend stage',stage,e.debug()))
   expected=np.broadcast_to(base,(160,240,3)).copy()
   if stage<2:
    for opacity in range(100):cell(expected,opacity%10*24,opacity//10*16,24,16,opacity,stage)
   else:
    for args in[(-5,-3,49,37,37,1),(60,30,99,75,37,1),(210,140,49,37,50,0)]:cell(expected,*args)
   path=out/f'{stage+1}.png';e.shot(path);actual=np.asarray(Image.open(path).convert('RGB'),dtype=np.int64)>>3;different=int(np.any(actual!=expected,axis=2).sum());rows.append({'stage':stage+1,'different_LCD_pixels':different});assert not different,rows[-1];e.frames(2,1);e.frames(2)
  result={'status':'pass','production_ROM_sha256':digest,'fixture_ROM_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'opacity_percentages':list(range(100)),'scope':'Actual LCD against independent scalar-channel RGB555 formula, two palettes of 100 opacity cases; tinted/clipped enlarged cells; bilinear image overwrites shared row before identical-alpha reuse. No running RAM writes.','checks':rows,'physical_hardware':'not_run'};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out.parent/'blend_latest.json').write_text(json.dumps({'report':str(out/'result.json'),'status':'pass'},ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))
 finally:e.close()
if __name__=='__main__':main()
