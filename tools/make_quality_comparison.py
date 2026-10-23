"""Label actual emulator captures; export untouched source images separately."""
import hashlib,json,struct,zipfile,zlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from project_env import ROOT,ARCHIVE,FONT
from portrait_assets import logical


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    build=json.loads((ROOT/'evidence/quality_preview/build.json').read_text());digest=build['ROM_sha256']
    case=ROOT/'evidence/quality_preview'/digest[:12]/'native/origin_1'
    old=ROOT/'evidence/quality_preview/baseline_v062';out=case.parents[1]/'comparison';out.mkdir(exist_ok=True)
    report=json.loads((case.parents[1]/'result.json').read_text());assert report['status']=='pass' and report['ROM_sha256']==digest
    font=ImageFont.truetype(str(FONT),24);small=ImageFont.truetype(str(FONT),19)
    def sheet(name,rows):
        im=Image.new('RGB',(1020,102+len(rows)*382+42),(23,25,29));d=ImageDraw.Draw(im)
        d.text((20,15),'v0.6.2 实际画面',font=font,fill='white');d.text((520,15),'RGB555 画质预览 · 实际画面',font=font,fill='white')
        d.text((20,53),'均为 GBA 模拟器截图，按整数 2 倍放大，无锐化',font=small,fill=(190,195,202))
        for i,(a,b,label) in enumerate(rows):
            y=96+i*382;d.text((20,y),label,font=small,fill=(230,230,225))
            for x,p in ((20,a),(520,b)):
                image=Image.open(p).convert('RGB');assert image.size==(240,160)
                im.paste(image.resize((480,320),Image.Resampling.NEAREST),(x,y+32))
        d.text((20,im.height-35),'原图仍受 GBA 240×160 / RGB555 限制；预览没有增加原素材中不存在的细节。',font=small,fill=(190,195,202))
        im.save(out/name)
    sheet('实际画质对照.png',[
        (old/'dialogue_000.png',case/'dialogue_000.png','开场同一段文字：旧版缩放并拟合颜色；本次原尺寸裁切、直接显示原色'),
        (old/'four_original_faces.png',case/'four_original_faces.png','同一组头像：原始 48×48；本次取消同屏头像之间的颜色近似')])
    sheet('标题与首次地图对照.png',[
        (old/'title.png',case/'title.png','标题：本次保留完整构图；左右留黑，未添加文字'),
        (old/'first_map.png',case/'first_map.png','首次地图：保留原探索遮罩；原本已正确的原尺寸地图不制造额外差异')])
    clean=Image.new('RGB',(1020,407),(23,25,29));d=ImageDraw.Draw(clean)
    for x,name,label in ((20,'original_illustration.png','隐藏文字查看原图 · 实际截图'),(520,'original_map_80_80.png','首次地图完整底图 · 实际截图')):
        d.text((x,14),label,font=font,fill='white');clean.paste(Image.open(case/name).resize((480,320),Image.Resampling.NEAREST),(x,52))
    d.text((20,379),'原尺寸显示，方向键浏览；地图全图查看仅供预览，不会改变探索进度。',font=small,fill=(190,195,202));clean.save(out/'原图浏览实际截图.png')
    original=out/'原素材参考_不是GBA截图';original.mkdir(exist_ok=True);sources=[]
    with zipfile.ZipFile(ARCHIVE)as z:
        names={logical(n):n for n in z.namelist()}
        for folder,name,label in [('Picture','風景・蓮','开场莲花'),('Panorama','背景・滝の洞窟','首次洞窟地图'),('Title','廃都タイトル2','原始标题'),('FaceSet','顔絵主役','原始头像表')]:
            path='Ruina121/game/'+folder+'/'+name+'.xyz';raw=z.read(names[path]);w,h=struct.unpack_from('<HH',raw,4);data=zlib.decompress(raw[8:]);im=Image.frombytes('P',(w,h),data[768:]);im.putpalette(data[:768]);im=im.convert('RGB');target=original/(label+'.png');im.save(target)
            sources.append({'original':path,'original_file_sha256':hashlib.sha256(raw).hexdigest(),'dimensions':[w,h],'export':str(target.relative_to(out)),'conversion':'exact indexed RGB8 to PNG; no resize, enhancement or generation'})
    record={'status':'created_from_actual_emulator_captures','baseline_ROM_sha256':build['base_v062_ROM_sha256'],'preview_ROM_sha256':digest,'screenshot_scale':'integer 2x nearest neighbour','sources':sources,'sheets':{p.name:sha(p)for p in out.glob('*.png')},'notes':['Native illustration and overview use different source viewports; labels disclose this.','The first map already used native-size cached art in v0.6.2; do not imply newly invented source detail.','Original PNG exports are source references, not emulator screenshots.']}
    (out/'result.json').write_text(json.dumps(record,ensure_ascii=False,indent=2));print(out)


if __name__=='__main__':main()
