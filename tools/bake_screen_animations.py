"""Precompose costly opaque screen layers, preserving every RGB555 pixel/mask.

Ordinary target-relative and translucent frames keep the original renderer.
Cached incremental rebuilding uses only the Python standard library.
"""
import array as A,hashlib,json,re,struct
from pathlib import Path
from project_env import ROOT
from inspect_lcf import data_root,array,integer
from check_animation_storage import unpack
from battle_animation_assets import compressor

def div(n,d):return n//d if n>=0 else -((-n)//d)
def signed(n):return n-0x100000000 if n>=0x80000000 else n
def clamp(n,lo,hi):return max(lo,min(hi,n))
def rectangles(rows):
 active={};finished=[]
 for y,row in enumerate(rows):
  now={};x=0
  while x<len(row):
   color=row[x];end=x+1
   while end<len(row)and row[end]==color:end+=1
   if color:
    key=(x,end-x,color)
    if key in active:rect=active.pop(key);rect[3]+=1
    else:rect=[x,y,end-x,1,color]
    now[key]=rect
   x=end
  finished.extend(active.values());active=now
 finished.extend(active.values());return finished

def main():
 out=ROOT/'build';manifest=out/'screen_animation_manifest.json';generation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();inputs={p:hashlib.sha256((out/p).read_bytes()).hexdigest()for p in('battle_animation_assets.h','battle_animations.bin','original/RPG_RT.ldb')}
 if manifest.exists():
  old=json.loads(manifest.read_text())
  if old.get('generator_sha256')==generation and old['source_inputs']==inputs and all((out/p).exists()and hashlib.sha256((out/p).read_bytes()).hexdigest()==h for p,h in old['cached_inputs'].items()):print(json.dumps({'screen_animations':'cached','frames':old['stored_frames'],'bank_bytes':old['bank_bytes']}));return
 bank=(out/'battle_animations.bin').read_bytes();header=(out/'battle_animation_assets.h').read_text();cells=[]
 pattern=r'\{\{original_animations_start\+(\d+),(\d+),(\d+),\(const u32\*\)\(original_animations_start\+(\d+)\),0,8,1,\d+,\d+,\(const u16\*\)\(original_animations_start\+(\d+)\),(\d+)\},(-?\d+),(-?\d+)\}'
 for m in re.finditer(pattern,header):
  offset,w,h,rows,pal,count,x,y=map(int,m.groups());bh=4096//w;blocks=(h+bh-1)//bh;indices=struct.unpack_from('<%dI'%(blocks+1),bank,rows);pixels=b''.join(unpack(bank[offset+indices[j]:offset+indices[j+1]],w*min(bh,h-j*bh))for j in range(blocks));colors=struct.unpack_from('<%dH'%count,bank,pal);cells.append((w,h,x,y,pixels,colors))
 sheets={name:[int(v)for v in values.split(',')]for name,values in re.findall(r'static const short (animation_sheet_\d+)\[\]=\{([^}]+)\}',header)};sheets={int(a):dict(zip(sheets[s][::2],sheets[s][1::2]))for a,s in re.findall(r'\{(\d+),(animation_sheet_\d+),sizeof',header)}
 animations=array(data_root((out/'original/RPG_RT.ldb').read_bytes())[1][19]);candidates=[];eligible=0;proven=0
 for aid,data in animations:
  if integer(data.get(9),0)!=1 or aid not in sheets:continue
  for fid,frame in array(data.get(12,b'')):
   specs=[];cost=0;valid=True
   for _,c in array(frame.get(1,b'')):
    if not integer(c.get(1),1):continue
    opacity=clamp(integer(c.get(10),0),0,100)
    if opacity==100:continue
    if opacity:valid=False;break
    cell_id=sheets[aid].get(integer(c.get(2),0),-1)
    if cell_id<0:continue
    sw,sh,ox,oy,pixels,colors=cells[cell_id];zoom=clamp(integer(c.get(5),100),0,2000);w=sw*zoom*3//400;h=sh*zoom*2//300
    if not w or not h:continue
    x=120+div((signed(integer(c.get(3),0))*100+ox*zoom)*3,400);y=53+div((signed(integer(c.get(4),0))*100+oy*zoom)*2,300);left=max(0,x);right=min(240,x+w);top=max(0,y);bottom=min(160,y+h)
    if left>=right or top>=bottom:continue
    tone=[clamp(integer(c.get(k),100),0,200)for k in range(6,10)];specs.append((cell_id,x,y,w,h,left,right,top,bottom,tone));cost+=(right-left)*(bottom-top)
   if not valid or not specs or not cost:continue
   eligible+=1;canvas=[32768]*38400
   for cell_id,x,y,w,h,left,right,top,bottom,tone in specs:
    sw,sh,ox,oy,pixels,source=cells[cell_id];colors=[]
    for color in source:
     r=color&31;g=color>>5&31;b=color>>10;gray=(r*30+g*59+b*11)//100;channels=[clamp(div((gray+div((v-gray)*tone[3],100))*tone[k],100),0,31)for k,v in enumerate((r,g,b))];colors.append(channels[0]|channels[1]<<5|channels[2]<<10)
    xs=[(xx-x)*sw//w for xx in range(left,right)];cached={}
    for yy in range(top,bottom):
     sy=(yy-y)*sh//h
     if sy not in cached:
      row=pixels[sy*sw:(sy+1)*sw];cached[sy]=[(left+i,colors[row[sx]])for i,sx in enumerate(xs)if row[sx]]
     at=yy*240
     for xx,color in cached[sy]:canvas[at+xx]=color
   colors=sorted(set(canvas)-{32768})
   if not colors or len(colors)>255:continue
   palette=[0]+colors;lut={c:i+1 for i,c in enumerate(colors)};lut[32768]=0;indexed=bytes(lut[c]for c in canvas);horizontal=rectangles([indexed[y*240:(y+1)*240]for y in range(160)]);vertical=rectangles([bytes(indexed[y*240+x]for y in range(160))for x in range(240)]);vertical=[[y,x,h,w,c]for x,y,w,h,c in vertical];rects=min((horizontal,vertical),key=len)
   restored=[32768]*38400
   for x,y,w,h,c in rects:
    for yy in range(y,y+h):restored[yy*240+x:yy*240+x+w]=[palette[c]]*w
   assert restored==canvas,(aid,fid);proven+=1;bounds=[min(r[0]for r in rects),min(r[1]for r in rects),max(r[0]+r[2]for r in rects),max(r[1]+r[3]for r in rects)];bounds[2]-=bounds[0];bounds[3]-=bounds[1]
   coverage=[0,0,0]
   for ty in range(10):
    for tx in range(8):
     width=min(32,240-tx*32);key=ty*8+tx
     if all(indexed[y*240+x]for y in range(ty*16,ty*16+16)for x in range(tx*32,tx*32+width)):coverage[key//32]|=1<<(key%32)
   cropped=b''.join(indexed[y*240+bounds[0]:y*240+bounds[0]+bounds[2]]for y in range(bounds[1],bounds[1]+bounds[3]))
   candidates.append({'id':aid,'frame':fid-1,'key':aid<<16|fid-1,'cost':cost,'palette':struct.pack('<%dH'%len(palette),*palette),'rects':bytes(v for r in rects for v in r),'indexed':cropped,'count':len(rects),'colors':len(palette),'bounds':bounds,'coverage':coverage,'RGB555_mask_sha256':hashlib.sha256(A.array('H',canvas).tobytes()).hexdigest()})
 compress=compressor()
 for row in candidates:
  encoded=bytearray();raw=row['rects']
  for start in range(0,len(raw),1000):
   chunk=raw[start:start+1000];packed=compress(chunk);assert unpack(packed,len(chunk))==chunk;encoded.extend(struct.pack('<HH',len(packed),len(chunk)//5));encoded.extend(packed)
  # Complex final layers are cheaper as native palette spans: one source
  # lookup per output pixel instead of thousands of tiny rectangle calls.
  # Simple enlarged blocks retain their constant-color rectangle fills.
  if row['count']*128>len(row['indexed']):
   indexed=bytearray();width=row['bounds'][2];raw=row['indexed'];chunks=[];chunk=bytearray();rows=0
   for start in range(0,len(raw),width):
    source=raw[start:start+width];spans=[];x=0
    while x<width:
     if not source[x]:x+=1;continue
     end=x+1
     while end<width and source[end]:end+=1
     spans.append(bytes((x,end-x))+source[x:end]);x=end
    line=bytes((len(spans),))+b''.join(spans)
    if len(chunk)+len(line)>1024:chunks.append((bytes(chunk),rows));chunk=bytearray();rows=0
    chunk.extend(line);rows+=1
   if chunk:chunks.append((bytes(chunk),rows))
   for chunk,rows in chunks:
    packed=compress(chunk);assert unpack(packed,len(chunk))==chunk;indexed.extend(struct.pack('<HHH',len(packed),rows,len(chunk)));indexed.extend(packed)
   encoded=indexed;row['count']=32768|row['bounds'][3];row['mode']='indexed_spans'
  else:row['mode']='rectangles'
  del row['indexed'];row['rects']=bytes(encoded)
 blob=bytearray();palettes={};streams={};stored=[];budget=1300000
 for row in sorted(candidates,key=lambda r:-r['cost']):
  p=row['palette'];s=row['rects'];extra=(len(p)+1 if p not in palettes else 0)+(len(s)if s not in streams else 0)
  if len(blob)+extra>budget:continue
  if p not in palettes:blob.extend(bytes((-len(blob))%2));palettes[p]=len(blob);blob.extend(p)
  if s not in streams:streams[s]=len(blob);blob.extend(s)
  stored.append({k:v for k,v in row.items()if k not in('palette','rects')});stored[-1].update(palette=palettes[p],stream=streams[s])
 stored.sort(key=lambda r:r['key']);code=['/* Exact opaque screen frames, generated from the original cells. */\nextern const u8 screen_animations_start[];\nstatic const ScreenAnimationFrame screen_animation_frames[]={\n']
 for r in stored:code.append('{%d,screen_animations_start+%d,(const u16*)(screen_animations_start+%d),%d,%d,{%s},{%s}},\n'%(r['key'],r['stream'],r['palette'],r['count'],r['colors'],','.join(map(str,r['bounds'])),','.join(str(v)+'U'for v in r['coverage'])))
 code.append('};\n');(out/'screen_animation_assets.h').write_text(''.join(code));(out/'screen_animations.bin').write_bytes(blob);(out/'screen_animation_blobs.s').write_text('.section .rodata.screen_animations,"a",%progbits\n.balign 4\n.global screen_animations_start\nscreen_animations_start:\n.incbin "build/screen_animations.bin"\n')
 result={'status':'pass','eligible_frames':eligible,'independently_reconstructed_frames':proven,'stored_frames':len(stored),'bank_bytes':len(blob),'budget_bytes':budget,'format':'Opaque final-layer RGB555 palettes with native indexed row blocks or nonoverlapping rectangles in lossless LZ4 chunks; exact transparent mask','all_reconstructed_RGB555_pixels_exact':True,'all_transparency_masks_exact':True,'generator_sha256':generation,'source_inputs':inputs,'records':stored,'cached_inputs':{p:hashlib.sha256((out/p).read_bytes()).hexdigest()for p in('screen_animation_assets.h','screen_animations.bin','screen_animation_blobs.s')}};manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('records','cached_inputs','source_inputs')},ensure_ascii=False))
if __name__=='__main__':main()
