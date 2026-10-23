"""Same genuine campaign SAV and town entry, before/after production ROMs.
Panels use nearest-neighbor integer enlargement of actual GBA screenshots.
"""
import hashlib,json,struct
from PIL import Image,ImageDraw,ImageFont
from drive_opening import ROOT,Emulator

def main():
 out=ROOT/'evidence/optimization_20261022/visual_comparison';out.mkdir(parents=True,exist_ok=True);rows=[]
 for label,base in [('v0.5.1',ROOT/'history/quality_performance_20261022/baseline/build'),('v0.6',ROOT/'build')]:
  rom=base/'废都物语_GBA_开篇开发验证版.gba';e=Emulator(ROOT/'history/legacy_checkpoint_v2.sav',rom=rom,elf=base/'ruina_opening_dev.elf')
  try:
   e.frames(30);e.key(1);e.key(128);e.key(1);e.frames(180);assert e.debug()[15]==4
   e.frames(2);e.shot(out/(label+'_cave.png'))
   for _ in range(100):
    if e.debug()[11]==21:break
    e.key(256)
   else:raise AssertionError(('return point',label,e.debug()))
   e.key(1)
   for _ in range(500):
    d=e.debug();assert d[15]!=5 and d[0]!=0x4641554c,d
    gmap=struct.unpack('<i',e.memory(e.symbols['game']+29768,4))[0]
    if d[15]==4 and gmap==3:break
    if d[15]in(1,2,12):e.key(1)
    else:e.frames(30)
   else:raise AssertionError(('town',label,e.debug()))
   e.frames(120);e.frames(2);e.shot(out/(label+'_town.png'))
   rows.append({'version':label,'rom_sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),'actual_map_and_position':list(struct.unpack('<3i',e.memory(e.symbols['game']+29768,12))),'kind':'actual production ROM, same genuine SAV, buttons, no memory writes or instant states','commands':e.log})
  finally:e.close()
 assert rows[0]['actual_map_and_position']==rows[1]['actual_map_and_position'],rows
 canvas=Image.new('RGB',(1008,790),'#151a22');draw=ImageDraw.Draw(canvas)
 font=ImageFont.truetype('/mnt/c/Windows/Fonts/simsun.ttc',22);small=ImageFont.truetype('/mnt/c/Windows/Fonts/simsun.ttc',17)
 draw.text((20,10),'实际 GBA 画面对照 · 同一存档与地点',font=font,fill='white')
 for col,label in enumerate(('v0.5.1','v0.6')):
  x=16+col*496;draw.text((x,45),label+('（之前）'if col==0 else'（本轮）'),font=font,fill='#e7d6a7')
  for row,scene in enumerate(('cave','town')):
   pic=Image.open(out/(label+'_'+scene+'.png')).convert('RGB');canvas.paste(pic.resize((480,320),Image.Resampling.NEAREST),(x,80+row*336))
 draw.text((20,755),'原生 240×160 截图仅放大 2 倍；未补画像素。全游戏和实机未验收。',font=small,fill='#c5ccd5');canvas.save(out/'画质对照.png')
 result={'status':'captured','production_rom_sha256':rows[-1]['rom_sha256'],'scope':'same source SAV, cave and Holm town; real GBA screenshots, integer enlargement only','captures':rows};(out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='captures'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
