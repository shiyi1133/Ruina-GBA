"""Compare actual old/new GBA captures; enlarge only by integer nearest-neighbor."""
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
from project_env import ROOT,FONT

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    digest=json.loads((ROOT/'build/build_receipt.json').read_text())['sha256']
    assert sha(ROOT/'build/废都物语_GBA_开篇开发验证版.gba')==digest
    old_digest='1db4e8b86af4cc3b4e71abdc983f9a8e5a2c84eb5784738258912a75750e1561'
    base=ROOT/'evidence/balanced_optimization_20261023';old=base/old_digest[:12]/'opening_1';new=base/digest[:12]/'opening_1'
    for folder,expected in((old,old_digest),(new,digest)):
        r=json.loads((folder/'result.json').read_text());assert r['status']=='pass'and r['ROM_sha256']==expected
    out=base/'visual_comparison';out.mkdir(exist_ok=True);font=ImageFont.truetype(str(FONT),24);small=ImageFont.truetype(str(FONT),18);records=[]
    def sheet(name,cases):
        canvas=Image.new('RGB',(1020,100+len(cases)*374+45),'#181b22');d=ImageDraw.Draw(canvas)
        d.text((20,14),'v0.6.2 · 实际旧版画面',font=font,fill='white');d.text((520,14),'v0.7 · 均衡画质可玩版',font=font,fill='white')
        d.text((20,55),'GBA 240×160 原生截图，整数 2 倍放大；无锐化、补画或生成细节。',font=small,fill='#c6ccd6')
        for i,(file,label)in enumerate(cases):
            y=95+i*374;d.text((20,y),label,font=small,fill='#e5d9ba')
            for x,folder in((20,old),(520,new)):
                p=folder/file;im=Image.open(p).convert('RGB');assert im.size==(240,160);canvas.paste(im.resize((480,320),Image.Resampling.NEAREST),(x,y+30));records.append({'file':str(p.relative_to(ROOT)),'sha256':sha(p),'native_size':[240,160]})
        d.text((20,canvas.height-34),'地图保留探索遮罩与原尺寸；少量地图颜色仍近似，完整流程和实机未验收。',font=small,fill='#c6ccd6');canvas.save(out/name)
    sheet('头像与插图对照.png',[('four_faces.png','同一组 48×48 头像：本版每组保留独立 RGB555 颜色'),('dialogue_000.png','同一开场插图：旧版缩放；本版原尺寸裁切显示，视野范围有所不同')])
    sheet('标题与地图对照.png',[('title.png','标题保留完整构图并使用缓存的高质量缩放'),('first_map.png','首次地图的原始像素与探索遮罩保留，不制造原素材中不存在的细节')])
    gallery=Image.new('RGB',(1020,806),'#181b22');d=ImageDraw.Draw(gallery);d.text((20,12),'v0.7 实际游戏画面',font=font,fill='white')
    phase=ROOT/'evidence/phase_demo_20261021'/digest[:12]
    for i,(p,label)in enumerate([(new/'four_faces.png','头像'),(phase/'first_battle.png','第一战'),(phase/'first_victory.png','探索'),(base/'music_room_long'/digest[:12]/'after_two_loops.png','音乐欣赏')]):
        x=20+(i%2)*500;y=55+(i//2)*365;d.text((x,y),label,font=small,fill='#e5d9ba');gallery.paste(Image.open(p).convert('RGB').resize((480,320),Image.Resampling.NEAREST),(x,y+26))
    gallery.save(out/'实际游戏画面.png')
    report={'status':'created_from_actual_GBA_screenshots','production_ROM_sha256':digest,'baseline_ROM_sha256':old_digest,'enlargement':'2x integer nearest-neighbor; no enhancement','screenshots':records,'sheets':{p.name:sha(p)for p in out.glob('*.png')},'viewport_note':'The first dialogue uses native-size cropping in the new build and reduced full-image layout in the old build; do not compare different source regions as invented detail.'}
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(out)

if __name__=='__main__':main()
