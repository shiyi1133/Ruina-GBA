"""Actual old/new mixed-sheet captures against the unchanged original bank.

Requires a separate rebuilt historical source project; never mix its objects
with the current production objects. The displayed scene is a controlled test.
"""
import argparse,hashlib,json,shutil,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from project_env import ROOT,FONT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def main():
    p=argparse.ArgumentParser();p.add_argument('--baseline-root',type=Path,required=True);args=p.parse_args();oldroot=args.baseline_root.resolve()
    old_pointer=read(oldroot/'evidence/optimization_20261022/portrait_matrix/latest_attempt.json');old_path=oldroot/old_pointer['report'];old=read(old_path)
    new_pointer=read(ROOT/'evidence/optimization_20261022/portrait_matrix/latest_stress_attempt.json');new_path=ROOT/new_pointer['report'];new=read(new_path)
    digest=read(ROOT/'build/build_receipt.json')['sha256'];assert new['status']=='pass'and new['production_rom_sha256']==digest and new['direct_RGB555_faces']
    assert old['status']=='pass'and old['production_rom_sha256']=='1db4e8b86af4cc3b4e71abdc983f9a8e5a2c84eb5784738258912a75750e1561'
    assert sha(ROOT/'build/portraits.bin')==sha(oldroot/'build/portraits.bin')==new['native_bank_sha256']==old['native_bank_sha256']
    bank=(ROOT/'build/portraits.bin').read_bytes();h=struct.unpack_from('<5I',bank);records=[struct.unpack_from('<HHI',bank,h[2]+i*8)for i in range(h[1])];available=[]
    def source(index):
        r=records[index];pixels=np.frombuffer(bank,np.uint8,2304,h[4]+r[2]).reshape(3,3,2,2,8,8).transpose(0,2,4,1,3,5).reshape(48,48)
        colors=np.frombuffer(bank,dtype='<u2',count=256,offset=h[3]+r[1]*512)[pixels]
        return np.stack((colors&31,colors>>5&31,colors>>10&31),axis=-1).astype(int),pixels!=0
    for row in old['rows']:
        if len(row['portraits'])<4:continue
        filename='%03d_sheets%03x.png'%(row['stage'],row['sheets_mask']);a=old_path.parent/filename;b=new_path.parent/filename
        if not a.exists()or not b.exists():continue
        newer=next(r for r in new['rows']if r['stage']==row['stage']);assert newer['portraits']==row['portraits']
        old_pixels=np.asarray(Image.open(a).convert('RGB')).astype(int)>>3;new_pixels=np.asarray(Image.open(b).convert('RGB')).astype(int)>>3;errors=[]
        for k,index in enumerate(row['portraits']):
            wanted,mask=source(index);counts=[];rmse=[]
            for actual in(old_pixels,new_pixels):
                delta=actual[24:72,8+k*58:56+k*58][mask]-wanted[mask];counts.append(int(np.any(delta!=0,axis=1).sum()));rmse.append(float(np.sqrt(np.mean(delta*delta))))
            assert counts[1]==0,(filename,index,counts)
            errors.append({'source_portrait_index':index,'source_image_id':records[index][0],'opaque_pixels':int(mask.sum()),'old_different_RGB555_pixels':counts[0],'new_different_RGB555_pixels':counts[1],'RGB555_channel_RMSE_before_after':rmse})
        available.append((sum(r['old_different_RGB555_pixels']for r in errors),a,b,row,errors))
    score,a,b,row,errors=max(available,key=lambda v:v[0]);assert score>0
    out=ROOT/'evidence/balanced_optimization_20261023/visual_comparison';raw=out/'mixed_portraits';raw.mkdir(parents=True,exist_ok=True);shutil.copy2(a,raw/'v062_actual.png');shutil.copy2(b,raw/'v07_actual.png')
    canvas=Image.new('RGB',(1020,440),'#181b22');d=ImageDraw.Draw(canvas);font=ImageFont.truetype(str(FONT),24);small=ImageFont.truetype(str(FONT),18)
    d.text((20,12),'v0.6.2 · 多组头像共用颜色',font=font,fill='white');d.text((520,12),'v0.7 · 各自保留原 RGB555 颜色',font=font,fill='white')
    for x,path in((20,a),(520,b)):canvas.paste(Image.open(path).convert('RGB').resize((480,320),Image.Resampling.NEAREST),(x,52))
    d.text((20,382),'受控同屏测试，非自然剧情截图。原始头像不缩小；仅整数 2 倍放大，无锐化。',font=small,fill='#c6ccd6')
    d.text((20,411),'只比较头像中非透明像素：旧版 %d 个像素近似颜色，本版 0 个。'%score,font=small,fill='#e5d9ba');target=out/'多组头像颜色对照.png';canvas.save(target)
    result={'status':'compared_actual_GBA_pixels','production_ROM_sha256':digest,'baseline_ROM_sha256':old['production_rom_sha256'],'baseline_fixture_sha256':old['fixture_sha256'],'current_fixture_sha256':new['fixture_sha256'],'original_portrait_bank_sha256':sha(ROOT/'build/portraits.bin'),'stage':row['stage'],'source_portrait_indices':row['portraits'],'faces':errors,'old_original_color_mismatches':score,'new_original_color_mismatches':0,'comparison':target.name,'comparison_sha256':sha(target),'captures':{p.name:sha(p)for p in raw.glob('*.png')},'scope':'Controlled mixed-FaceSet fixture, actual GBA LCD screenshots; original nontransparent source pixels converted to RGB555. No enhancement and no claim that this scene occurs in the natural campaign.'}
    (raw/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));sheet=read(out/'result.json');sheet['mixed_portrait_comparison']=str((raw/'result.json').relative_to(ROOT));sheet['sheets'][target.name]=sha(target);(out/'result.json').write_text(json.dumps(sheet,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
