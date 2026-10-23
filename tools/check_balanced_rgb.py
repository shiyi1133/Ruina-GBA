"""Independent source-PNG RGB555 comparisons for the balanced renderer."""
import argparse,hashlib,json,re,struct
import numpy as np
from PIL import Image
from drive_opening import ROOT,Emulator
from gba_fixture import fixture
from build_balanced_runtime import OVERRIDES

def main():
    p=argparse.ArgumentParser();p.add_argument('--video');p.add_argument('--extra-native',action='store_true');args=p.parse_args()
    metadata=json.loads((ROOT/'build/asset_manifest.json').read_text());names=metadata['images'];cases=[]
    def add(image,x,y,sx,sy,sw,sh,w,h,transparent=0,opacity=0,tone=None,clip=(0,0,240,160)):
        cases.append([image,x,y,sx,sy,sw,sh,w,h,transparent,opacity,int(tone is not None),*(tone or[100]*4),*clip])
    for image in(1,3,5,6,7,160,446,499,506,514):
        meta=metadata['image_storage'][image];w,h=meta['width'],meta['height']
        add(image,-17,-11,0,0,min(w,240),min(h,160),min(w,240),min(h,160),1)
        add(image,9,7,0,0,w,h,213,142,1,25)
        add(image,-13,5,0,0,w,h,267,133,0,70,[80,110,90,50],(7,11,221,136))
    for opacity in(0,25,70,100):
        add(446,-10,-10,-7,-5,90,70,180,140,1,opacity)
        add(506,1,3,40,20,180,130,227,143,1,opacity,[110,90,75,30])
    add(506,0,0,-30,-20,300,210,240,160,1)
    add(506,0,0,300,220,50,50,100,100,1)
    add(0,0,0,0,0,240,160,240,160,0,0,[80,110,90,50])
    if args.extra_native:
        add(506,0,0,40,0,240,160,240,160)
        add(506,0,0,40,0,240,160,240,160,1)
        add(506,-16,-8,8,16,256,176,256,176,1,0,[80,110,90,50],(8,8,216,136))
    (ROOT/'build/balanced_rgb_cases.h').write_text('static const int rgb_cases[][20]={'+','.join('{'+','.join(map(str,c))+'}'for c in cases)+'};\n')
    rom,elf,base=fixture('tests/balanced_rgb_gba.c','balanced_rgb_trial'if args.video else'balanced_rgb',{**OVERRIDES,**({'video':args.video}if args.video else{})});digest=hashlib.sha256(rom.read_bytes()).hexdigest()
    out=ROOT/'evidence/balanced_optimization_20261023/rgb_pixels'/digest[:12];out.mkdir(parents=True,exist_ok=True)
    source=(ROOT/'build/assets.c').read_text();pal=np.array([int(v)for v in re.search(r'game_palette\[256\]\s*=\s*\{([^}]+)\}',source).group(1).split(',')],dtype=np.int64)
    def channels(p):return np.stack((p&31,p>>5&31,p>>10&31),axis=-1)
    palette=channels(pal);grid=np.arange(256).reshape(16,16).repeat(10,0).repeat(15,1)
    def expected(c):
        image,x,y,sx,sy,sw,sh,w,h,transparent,opacity,toned,*tail=c;tone=np.array(tail[:4],dtype=np.int64);cx,cy,cw,ch=tail[4:]
        out=palette[grid].copy();im=Image.open(ROOT/'build'/(names[image]+'_palette.png'));raw=np.asarray(im);colors=np.array(im.getpalette(),dtype=np.int64).reshape(256,3)>>3
        if toned:
            gray=(colors[:,0]*30+colors[:,1]*59+colors[:,2]*11)//100
            colors=gray[:,None]+np.trunc((colors-gray[:,None])*tone[3]/100).astype(np.int64)
            colors=np.clip(np.trunc(colors*tone[:3]/100).astype(np.int64),0,31)
        if opacity>=100:return out
        left=max(0,cx,x);right=min(240,cx+cw,x+w);top=max(0,cy,y);bottom=min(160,cy+ch,y+h)
        if right<=left or bottom<=top:return out
        xx=np.arange(left,right);yy=np.arange(top,bottom);alpha=(100-max(0,min(100,opacity)))*256//100
        near_x=sx+(xx-x)*sw//w;near_y=sy+(yy-y)*sh//h;valid_x=(near_x>=0)&(near_x<raw.shape[1]);valid_y=(near_y>=0)&(near_y<raw.shape[0]);valid=valid_y[:,None]&valid_x[None,:]
        old=out[top:bottom,left:right]
        if w==sw and h==sh:
            index=raw[np.clip(near_y,0,raw.shape[0]-1)[:,None],np.clip(near_x,0,raw.shape[1]-1)[None,:]];rgb=colors[index];valid&=(index!=0)if transparent else True
            result=(rgb*alpha+old*(256-alpha)+128)>>8
        else:
            fx=((2*(xx-x)+1)*sw*128//w)-128+sx*256;fy=((2*(yy-y)+1)*sh*128//h)-128+sy*256
            x0=fx>>8;y0=fy>>8;wx=np.where((x0<0)|(x0>=raw.shape[1]-1),0,fx&255);wy=np.where((y0<0)|(y0>=raw.shape[0]-1),0,fy&255)
            x0=np.clip(x0,0,raw.shape[1]-1);y0=np.clip(y0,0,raw.shape[0]-1);x1=x0+(wx!=0);y1=y0+(wy!=0)
            values=[raw[y0[:,None],x0[None,:]],raw[y0[:,None],x1[None,:]],raw[y1[:,None],x0[None,:]],raw[y1[:,None],x1[None,:]]]
            weights=[(256-wy[:,None])*(256-wx[None,:]),(256-wy[:,None])*wx[None,:],wy[:,None]*(256-wx[None,:]),wy[:,None]*wx[None,:]]
            total=np.zeros(valid.shape,dtype=np.int64);rgb=np.zeros(old.shape,dtype=np.int64)
            for index,weight in zip(values,weights):
                weight=weight*((index!=0)if transparent else 1);total+=weight;rgb+=colors[index]*weight[:,:,None]
            result=(rgb*alpha+old*((1<<24)-total[:,:,None]*alpha)+(1<<23))>>24
            exact=(total==65536)&(alpha==256);result[exact]=rgb[exact]>>16
        old[valid]=result[valid];return out
    e=Emulator(rom=rom,elf=elf);checks=[]
    try:
        for stage,case in enumerate(cases,1):
            for _ in range(1000):
                if e.debug()[14]==stage:break
                e.frames(10)
            else:raise AssertionError(('stage',stage,e.debug()))
            e.frames(2);p=out/f'{stage:03}.png';e.shot(p);actual=np.array(Image.open(p).convert('RGB'),dtype=np.int64)>>3;wanted=expected(case)
            diff=int(np.any(actual!=wanted,axis=2).sum());checks.append({'stage':stage,'case':case,'different_pixels':diff})
            if diff:Image.fromarray((wanted*8).astype(np.uint8)).save(out/f'{stage:03}_expected.png')
            e.frames(2,1);e.frames(2)
        result={'status':'pass'if not any(v['different_pixels']for v in checks)else'fail','production_baseline_SHA256':base,'fixture_SHA256':digest,'video_source_override':args.video,'extra_native':args.extra_native,'whole_tile_metrics':list(struct.unpack('<2I',e.memory(e.symbols['balanced_rgb_whole_tiles'],8)))if'balanced_rgb_whole_tiles'in e.symbols else None,'renderer_source_sha256':json.loads((ROOT/'build/build_receipt.json').read_text())['compiler_inputs_sha256'],'checks':checks,'scope':'Actual GBA LCD against independent PNG-based RGB555 alpha, tint, native crop, bilinear, clipping and source-boundary arithmetic. No patched emulator RAM.','hardware':'not_run','commands':e.log}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('commands','renderer_source_sha256')},ensure_ascii=False,indent=2));assert result['status']=='pass'
    finally:e.close()

if __name__=='__main__':main()
