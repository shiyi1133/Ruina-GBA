"""Precompute the static title from original art; normal builds use the cache."""
import hashlib,json,struct,zipfile,zlib
import numpy as np
from PIL import Image
from project_env import ROOT,ARCHIVE
from portrait_assets import logical

def main():
    name='Ruina121/game/Title/廃都タイトル2.xyz'
    with zipfile.ZipFile(ARCHIVE)as z:
        names={logical(n):n for n in z.namelist()};raw=z.read(names[name])
    w,h=struct.unpack_from('<HH',raw,4);data=zlib.decompress(raw[8:]);im=Image.frombytes('P',(w,h),data[768:]);im.putpalette(data[:768]);im=im.convert('RGB');im.thumbnail((240,160),Image.Resampling.LANCZOS)
    canvas=Image.new('RGB',(240,160));canvas.paste(im,((240-im.width)//2,(160-im.height)//2));rgb=np.asarray(canvas).astype(np.uint16)>>3;pixels=rgb[...,0]|rgb[...,1]<<5|rgb[...,2]<<10
    out=ROOT/'platform/gba';out.mkdir(exist_ok=True);(out/'title_rgb555.h').write_text('static const unsigned short balanced_title_rgb555[38400] __attribute__((aligned(4)))={'+','.join(map(str,pixels.ravel()))+'};\n')
    receipt={'source':name,'source_sha256':hashlib.sha256(raw).hexdigest(),'source_dimensions':[w,h],'output_dimensions':[240,160],'method':'aspect-preserving Lanczos, black letterbox, RGB555','cached_header_sha256':hashlib.sha256((out/'title_rgb555.h').read_bytes()).hexdigest()};(out/'title_asset.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
