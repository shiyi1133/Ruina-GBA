"""Cache the exact existing native-map UI tiles; no art replacement."""
import hashlib,json,re
from pathlib import Path
from project_env import ROOT

def hints():
    source=(ROOT/'build/assets.c').read_text()
    codes=[int(v)for v in re.search(r'glyph_codes\[[^]]+\]=\{([^}]+)\}',source).group(1).split(',')]
    rows=[[int(v)for v in row.split(',')]for row in re.findall(r'\{([^{}]+)\}',re.search(r'glyph_rows\[\]\[12\]=\{(.*?)\};',source,re.S).group(1))]
    glyphs=dict(zip(codes,rows));directions=bytearray(11*64);selection=bytearray(2*256);labels=bytearray(2*512)
    for t in range(11):
        for y in range(8):
            for x in range(8):
                color=0
                if t<8:
                    d=t//2;a=7-x if d==1 else x if d==3 else y;b=y if d in(1,3)else x
                    if d==2:a=7-y
                    if 1<=a<=6 and 3-a//2<=b<=4+a//2:color=12 if t&1 else 2
                else:
                    dx=3-x if x<4 else x-4;dy=3-y if y<4 else y-4
                    if dx+dy<=3:color=14 if dx+dy==3 else 2 if t==8 else 5 if t==9 else 12
                    if dx+dy<1:color=13
                directions[t*64+y*8+x]=color
    for t in range(2):
        for y in range(16):
            for x in range(16):
                c=14 if x in(0,15)or y in(0,15)else(13 if t else 2)if x in(1,14)or y in(1,14)else 0
                tile=y//8*2+x//8;at=y%8*8+x%8;selection[t*256+tile*64+at]=c
    for state,label in enumerate(('调查','受阻')):
        for y in range(16):
            for x in range(32):
                c=11
                if x in(0,31)or y in(0,15):c=12 if state else 2
                elif 4<=x<28 and 2<=y<14:
                    glyph=glyphs[int.from_bytes(label[(x-4)//12].encode('gbk'),'big')]
                    if glyph[y-2]&(1<<(11-(x-4)%12)):c=12 if state else 1
                tile=y//8*4+x//8;at=y%8*8+x%8;labels[state*512+tile*64+at]=c
    return [('directions',bytes(directions),0x06016000),('selection',bytes(selection),0x06016500),('labels',bytes(labels),0x06017a00)]

def main():
    target=ROOT/'platform/gba';parts=[];report=[]
    for name,data,address in hints():
        values=[int.from_bytes(data[i:i+4],'little')for i in range(0,len(data),4)]
        parts.append('static const u32 balanced_hint_'+name+'[]={'+','.join(str(x)for x in values)+'};\n')
        report.append({'name':name,'bytes':len(data),'VRAM_address':hex(address),'sha256':hashlib.sha256(data).hexdigest()})
    (target/'map_hints.h').write_text('/* Generated exact pre-existing map hint tiles; tools/balanced_map_hint_asset.py. */\n'+''.join(parts))
    (target/'map_hint_asset.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
