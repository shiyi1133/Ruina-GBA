"""Adapt original art to GBA; preserve music sources without new arrangements.

This exports art/font data only. Audio support is unfinished; exporting a source
MIDI is not evidence that the GBA runtime plays it correctly.
"""
from pathlib import Path
import zipfile,json,zlib,struct,hashlib,re
import numpy as np
from PIL import Image,ImageFont
from image_codec import encode_row,decode_row,encode_lz4
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build';OUT.mkdir(exist_ok=True)
from project_env import ARCHIVE,FONT
def logical(n):
 try:return n.encode('gbk').decode('cp932')
 except UnicodeError:return n
z=zipfile.ZipFile(ARCHIVE);names={logical(n):n for n in z.namelist()};used=[]
def raw(folder,name):
 key='Ruina121/game/'+folder+'/'+name;data=z.read(names[key]);used.append({'file':key,'sha256':hashlib.sha256(data).hexdigest()});return data
def xyz(folder,name):
 b=raw(folder,name+'.xyz');w,h=struct.unpack('<HH',b[4:8]);d=zlib.decompress(b[8:]);im=Image.frombytes('P',(w,h),d[768:]);im.putpalette(d[:768]);return im.convert('RGB')
imgs=[];labels=[]
def add(name,im):labels.append(name);imgs.append(im.convert('RGB'));return len(imgs)-1
title=xyz('Title','廃都タイトル2');add('title',title.resize((240,180),Image.Resampling.LANCZOS).crop((0,0,240,160)))
cave=xyz('Panorama','背景・滝の洞窟');add('cave',cave)
town=xyz('Panorama','背景・ホルムの町');add('town',town)
add('tavern',xyz('Panorama','背景・酒場'))
scene=xyz('Picture','風景・滝の洞窟');add('lake',scene.resize((240,120),Image.Resampling.LANCZOS))
add('forest',xyz('Picture','風景・蓮').resize((240,120),Image.Resampling.LANCZOS))
back=xyz('Backdrop','背景・洞窟')if 'Ruina121/game/Backdrop/背景・洞窟.xyz'in names else xyz('Backdrop','背景・森')if 'Ruina121/game/Backdrop/背景・森.xyz'in names else None
if back is None:
 key=next(n for n in names if'/Backdrop/'in n and n.endswith('.xyz'));back=xyz('Backdrop',Path(key).stem)
add('battle_bg',back.resize((240,120),Image.Resampling.LANCZOS))
# Native actor portraits and original monsters. Palette index 0 in monster XYZs is transparent.
faces=xyz('FaceSet','顔絵主役');companions=xyz('FaceSet','顔絵仲間１')
for i in range(16):
 name='hero'+str(i);x=(i%4)*48;y=(i//4)*48;add(name,faces.crop((x,y,x+48,y+48)).resize((36,36),Image.Resampling.NEAREST))
add('laban',companions.crop((96,0,144,48)).resize((36,36),Image.Resampling.NEAREST))
for name,file in [('worm','ニョロ'),('bat','m412b　こうもりb'),('knight','95死霊の騎士'),('goblin','小鬼')]:
 b=raw('Monster',file+'.xyz');w,h=struct.unpack('<HH',b[4:8]);d=zlib.decompress(b[8:]);p=Image.frombytes('P',(w,h),d[768:]);p.putpalette(d[:768]);im=p.convert('RGBA');im.putalpha(p.point(lambda v:0 if v==0 else 255,'L'));im.thumbnail((78,66),Image.Resampling.LANCZOS);add(name,im.convert('RGB'));imgs[-1]=im
# Resolve monster art from original enemy resource names, including random
# encounters, instead of substituting a single generic enemy image.
enemy_ids=[-1]*261;monster_ids={}
for row in json.loads((ROOT/'research/database.json').read_text())['enemies']:
 b=bytes.fromhex(row['fields'].get('2',''));name=b.decode('cp932')
 if not name or 'Ruina121/game/Monster/'+name+'.xyz'not in names:continue
 if name not in monster_ids:
  data=raw('Monster',name+'.xyz');w,h=struct.unpack('<HH',data[4:8]);pixels=zlib.decompress(data[8:]);p=Image.frombytes('P',(w,h),pixels[768:]);p.putpalette(pixels[:768]);im=p.convert('RGBA');im.putalpha(p.point(lambda v:0 if v==0 else 255,'L'));im.thumbnail((78,66),Image.Resampling.LANCZOS);idx=add('monster'+str(len(monster_ids)),im);imgs[idx]=im;monster_ids[name]=idx
 enemy_ids[row['id']]=monster_ids[name]
scene_tables=[]
for name in ['風景・蓮','風景・河の娘','風景・領主の館2','風景・怪盗二人','風景・親子','風景・領主の館夜','風景・滝の洞窟']:
 idx=labels.index('forest')if name=='風景・蓮'else labels.index('lake')if name=='風景・滝の洞窟'else add('story'+str(len(scene_tables)),xyz('Picture',name).resize((240,120),Image.Resampling.LANCZOS));scene_tables.append((name,idx))
map_ids=[-1]*73;panorama_ids={}
for m in json.loads((ROOT/'research/maps.json').read_text()):
 if not m['background']:continue
 if m['id']in[3,4,23]:map_ids[m['id']]=labels.index({3:'town',4:'tavern',23:'cave'}[m['id']])
 elif m['background']in panorama_ids:map_ids[m['id']]=panorama_ids[m['background']]
 else:map_ids[m['id']]=add('map'+str(m['id']),xyz('Panorama',m['background']))
 panorama_ids[m['background']]=map_ids[m['id']]
def namehash(s):
 h=2166136261
 for b in s:h=((h^b)*16777619)&0xffffffff
 return h
face_tables=[]
for key in sorted(names):
 if '/FaceSet/' not in key or not key.endswith('.xyz'):continue
 sheetname=Path(key).stem;sheet=xyz('FaceSet',sheetname);ids=[]
 for i in range(16):
  if sheetname=='顔絵主役':ids.append(labels.index('hero'+str(i)));continue
  x=i%4*48;y=i//4*48;ids.append(add('face'+str(len(face_tables))+'_'+str(i),sheet.crop((x,y,x+48,y+48)).resize((36,36),Image.Resampling.NEAREST)))
 face_tables.append((namehash(sheetname.encode('cp932')),ids))
resource_tables=[]
for kind,folder in enumerate(['Picture','Panorama','ChipSet','CharSet','Backdrop']):
 for key in sorted(names):
  if '/'+folder+'/'not in key or not key.endswith('.xyz'):continue
  name=Path(key).stem
  if folder=='Panorama'and name in panorama_ids:idx=panorama_ids[name]
  else:
   b=raw(folder,name+'.xyz');w,h=struct.unpack('<HH',b[4:8]);d=zlib.decompress(b[8:]);p=Image.frombytes('P',(w,h),d[768:]);p.putpalette(d[:768]);im=p.convert('RGBA')if folder in ['Picture','ChipSet','CharSet']else p.convert('RGB')
   if im.mode=='RGBA':im.putalpha(p.point(lambda v:0 if v==0 else 255,'L'))
   idx=add('resource'+str(len(resource_tables)),im);imgs[idx]=im
  resource_tables.append((kind,namehash(name.encode('cp932')),idx))
ui=[(25,24,29),(247,235,209),(219,177,99),(77,172,135),(220,92,85),(106,164,207),(174,154,123),(231,207,164),(59,49,45),(100,83,60),(170,213,180),(15,19,25),(108,97,95),(255,255,255),(0,0,0),(185,158,111)]
samples=Image.new('RGB',(512,128*((len(imgs)+3)//4)));at=0
for im in imgs:
 t=im.convert('RGB');t.thumbnail((128,128));samples.paste(t,((at%4)*128,(at//4)*128));at+=1
colors=samples.quantize(colors=240,method=Image.Quantize.MEDIANCUT).getpalette()[:720];palette=sum(([r,g,b]for r,g,b in ui),[])+colors;palette=palette[:768]+[0]*max(0,768-len(palette))
palim=Image.new('P',(1,1));palim.putpalette(palette)
if '--legacy-palette'in __import__('sys').argv:
 arrays=[];infos=[];image_storage=[]
 native_ids={i for kind,_,i in resource_tables if kind in (1,2,3)}
 shared_palettes={}
 def palette_array(name,values):
  key=bytes(values)
  if key in shared_palettes:return shared_palettes[key]
  symbol='palette_'+name;shared_palettes[key]=symbol;arrays.append(cbytes(symbol,values));return symbol
 def cbytes(name,data,ctype='unsigned char'):
  return f'const {ctype} {name}[{len(data)}]={{'+','.join(str(int(v))for v in data)+'};\n'
 for i,(name,im)in enumerate(zip(labels,imgs)):
  virtual_width,virtual_height=im.size
  # Preserve original coordinates and dimensions in the runtime. Only raster
  # detail is reduced, as authorized, so large later-game assets fit 32 MiB.
  if i not in native_ids and im.width*im.height>240*120:im=im.resize((max(1,im.width*3//4),max(1,im.height*3//4)),Image.Resampling.NEAREST)
  assert im.width<=1024
  alpha=im.mode=='RGBA';q=im.convert('RGB').quantize(colors=15 if alpha else 16,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE);a=np.asarray(q).copy();local=np.asarray(q.getpalette(),dtype=np.int32).reshape(-1,3)[:15 if alpha else 16];global_colors=np.asarray(palette,dtype=np.int32).reshape(256,3)
  mapping=[]
  for color in local:
   lo=1 if alpha else 0;mapping.append(lo+int(np.argmin(np.sum((global_colors[lo:]-color)**2,axis=1))))
  if alpha:a+=1;a[np.asarray(im.getchannel('A'))<128]=0;mapping=[0]+mapping
  mapping=mapping+[0]*(16-len(mapping));blob=bytearray();offsets=[0]
  for row in a:
   packed=encode_row(row);assert decode_row(packed,len(row))==bytes(row);blob.extend(packed);offsets.append(len(blob))
  packed_rows=bytearray()
  for row in a:
   for i in range(0,len(row),2):packed_rows.append(int(row[i])<<4|(int(row[i+1])if i+1<len(row)else 0))
  stride=(im.width+1)//2;blocks=bytearray();block_offsets=[0]
  for y in range(0,im.height,8):blocks.extend(encode_lz4(packed_rows[y*stride:(y+8)*stride]));block_offsets.append(len(blocks))
  encoding=1
  if len(blocks)+4*len(block_offsets)<len(blob)+4*len(offsets):blob=blocks;offsets=block_offsets;encoding=2
  # Larger lossless blocks reuse the same bounded 4096-byte decoder cache.
  # This recovers ROM space for original-resolution panoramas and map sprites.
  lines=4096//stride;adaptive=bytearray();adaptive_offsets=[0]
  for y in range(0,im.height,lines):adaptive.extend(encode_lz4(packed_rows[y*stride:(y+lines)*stride]));adaptive_offsets.append(len(adaptive))
  if len(adaptive)+4*len(adaptive_offsets)<len(blob)+4*len(offsets):blob=adaptive;offsets=adaptive_offsets;encoding=4
  symbol=palette_array(name,mapping)
  arrays.append(cbytes('img_'+name,blob));arrays.append(cbytes('rows_'+name,offsets,'unsigned int'));infos.append(f'{{img_{name},{virtual_width},{virtual_height},rows_{name},{symbol},{encoding},{int(alpha)},{im.width},{im.height}}}')
  rendered=Image.fromarray(np.asarray(mapping,dtype=np.uint8)[a],mode='P');rendered.putpalette(palette);rendered.save(OUT/(name+'_palette.png'))
  image_storage.append({'image':name,'width':virtual_width,'height':virtual_height,'stored_width':im.width,'stored_height':im.height,'encoding':encoding,'bytes':len(blob)+4*len(offsets)+16,'pixels':virtual_width*virtual_height})
 # Independent 8x8 chipset pieces avoid repeatedly decompressing a full atlas
 # while drawing a tile. Pixels match the virtual atlas exactly, including fog.
 chip_ids=[];chip_quads=[];quad_cache={}
 for kind,hash_value,image_id in resource_tables:
  if kind!=2:continue
  meta=image_storage[image_id];stored=Image.open(OUT/(meta['image']+'_palette.png'))
  a=np.asarray(stored);virtual=a[np.arange(meta['height'])*stored.height//meta['height']][:,np.arange(meta['width'])*stored.width//meta['width']]
  ids=[]
  for yy in range(0,256,8):
   for xx in range(0,480,8):
    data=virtual[yy:yy+8,xx:xx+8].tobytes()
    if data not in quad_cache:
     name='chipquad'+str(len(quad_cache));idx=len(labels);quad_cache[data]=idx;labels.append(name)
     local_colors=sorted(set(data));assert len(local_colors)<=16
     codes={v:i for i,v in enumerate(local_colors)};packed=bytes(codes[data[i]]<<4|codes[data[i+1]]for i in range(0,64,2))
     symbol=palette_array(name,local_colors+[0]*(16-len(local_colors)))
     arrays.append(cbytes('img_'+name,packed));infos.append(f'{{img_{name},8,8,0,{symbol},3,1,0,0}}')
     rendered=Image.frombytes('P',(8,8),data);rendered.putpalette(palette);rendered.save(OUT/(name+'_palette.png'))
     image_storage.append({'image':name,'width':8,'height':8,'stored_width':8,'stored_height':8,'encoding':3,'bytes':48,'pixels':64})
    ids.append(quad_cache[data])
  chip_ids.append(image_id);chip_quads.append(ids)
 arrays.append(cbytes('chip_image_ids',chip_ids,'short'))
 arrays.append('const unsigned short chip_quad_image_ids[][1920]={'+','.join('{'+','.join(str(x)for x in row)+'}'for row in chip_quads)+'};\n')
 arrays.append('const unsigned chip_image_count='+str(len(chip_ids))+';\n')
 arrays.append('const ScenePalette image_scenes[1]={{0,0,0,0}};\nconst unsigned image_scene_count=0;\n')
else:
 from high_color_assets import convert_images,cbytes
 arrays,infos,image_storage=convert_images(imgs,labels,resource_tables,OUT,palette)
pal=[(palette[i]>>3)|((palette[i+1]>>3)<<5)|((palette[i+2]>>3)<<10)for i in range(0,768,3)]
arrays.append(cbytes('game_palette',pal,'unsigned short'))
arrays.append('const Image images[]={'+','.join(infos)+'};\n')
exfont=xyz('Font','EXFONT').convert('L');icon_rows=[]
assert exfont.size==(156,48)
for i in range(52):
 x0=i%13*12;y0=i//13*12
 icon_rows.append([sum(1<<(11-x)for x in range(12)if exfont.getpixel((x0+x,y0+y))>=128)for y in range(12)])
arrays.append('const unsigned short exfont_rows[52][12]={'+','.join('{'+','.join(str(n)for n in row)+'}'for row in icon_rows)+'};\n')
arrays.append(cbytes('map_image_ids',map_ids,'short'))
arrays.append(cbytes('enemy_image_ids',enemy_ids,'short'))
arrays.append(cbytes('story_name_hashes',[namehash(n.encode('cp932'))for n,i in scene_tables],'unsigned int'))
arrays.append(cbytes('story_image_ids',[i for n,i in scene_tables],'short'))
arrays.append(cbytes('face_name_hashes',[x[0]for x in face_tables],'unsigned int'))
arrays.append('const short face_image_ids[][16]={'+','.join('{'+','.join(str(i)for i in ids)+'}'for _,ids in face_tables)+'};\n')
arrays.append('const ResourceImage resource_images[]={'+','.join('{%d,%dU,%d}'%r for r in resource_tables)+'};\n')
arrays.append('const unsigned resource_image_count=sizeof(resource_images)/sizeof(resource_images[0]);\n')
header='\n'.join(f'#define IMG_{n.upper()} {i}'for i,n in enumerate(labels))+'\n'
header+=f'#define FACE_SHEET_COUNT {len(face_tables)}\n#define STORY_IMAGE_COUNT {len(scene_tables)}\n'
audio_meta=[]
# Keep complete source tracks, including the actual scene19 creation music.
# Native playback must retain original programs, drums, tempo and loop behavior.
audio_dir=OUT/'audio_source';audio_dir.mkdir(exist_ok=True)
for file in ['scene19.mid','Tale.mid','ダンジョン4.mid','1stEnemy.mid']:
 key='Ruina121/game/Music/'+file
 if key not in names:continue
 data=raw('Music',file);(audio_dir/file).write_bytes(data)
 audio_meta.append({'track':file,'kind':'unchanged original source','sha256':hashlib.sha256(data).hexdigest(),'gba_playback':'see separate runtime audio evidence'})
for key in names:
 if key.lower().endswith('.soundfont'):
  data=z.read(names[key]);(audio_dir/Path(key).name).write_bytes(data)
  used.append({'file':key,'sha256':hashlib.sha256(data).hexdigest()})
# Original dialogue is the font source, not newly authored replacement prose.
text_sources=[]
def collect(value):
 if isinstance(value,dict):
  for k,v in value.items():
   if k in ('text','name') and isinstance(v,str):text_sources.append(v)
   elif isinstance(v,(dict,list)):collect(v)
 elif isinstance(value,list):
  for v in value:collect(v)
if (OUT/'music_room_names.c').exists():text_sources.append((OUT/'music_room_names.c').read_text())
for file in ['maps.json','common_events.json','database.json']:
 collect(json.loads((ROOT/'research'/file).read_text()))
for folder in ['source','runtime/rm2k','platform/gba']:
 for file in (ROOT/folder).glob('*.c'):text_sources.append(file.read_text())
# Include descriptions and database terminology, not just table entry names.
database=json.loads((ROOT/'research/database.json').read_text())
for table,fields in [('actors',[1,2,67]),('skills',[1,2,3,4]),('items',[1,2]),('enemies',[1])]:
 for row in database[table]:
  for field in fields:
   if str(field) in row['fields']:
    text_sources.append(bytes.fromhex(row['fields'][str(field)]).decode('gbk',errors='strict'))
src=''.join(text_sources)+''.join(chr(c)for c in range(32,127))
def gbkcode(c):
 try:
  b=c.encode('gbk');return int.from_bytes(b,'big') if 1<=len(b)<=2 else None
 except UnicodeEncodeError:return None
chars=[c for c in set(src) if ord(c)>=32 and gbkcode(c) is not None]
chars.sort(key=gbkcode)
glyphs=[];font=ImageFont.truetype(str(FONT),12)
from PIL import ImageDraw
for c in chars:
 im=Image.new('1',(12,12));draw=ImageDraw.Draw(im);draw.text((0,-1),c,font=font,fill=1)
 glyphs.append([sum((1<<(11-x))for x in range(12)if im.getpixel((x,y)))for y in range(12)])
arrays.append(cbytes('glyph_codes',[gbkcode(c)for c in chars],'unsigned short'));arrays.append('const unsigned short glyph_rows[][12]={'+','.join('{'+','.join(str(v)for v in row)+'}'for row in glyphs)+'};\n');header+=f'#define GLYPH_COUNT {len(chars)}\n'
(OUT/'assets.h').write_text(header);(OUT/'assets.c').write_text('#include "types.h"\n'+''.join(arrays));(OUT/'asset_manifest.json').write_text(json.dumps({'archive_sha256':hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),'source_assets':used,'images':labels,'image_storage':image_storage,'encoded_image_bytes':sum(r['bytes']for r in image_storage),'resources':[{'kind':k,'hash':h,'image':i}for k,h,i in resource_tables],'audio':audio_meta,'glyph_count':len(chars)},ensure_ascii=False,indent=2))
print('ASSETS',len(labels),'FONT',len(chars),'UNCHANGED AUDIO SOURCES',len(audio_meta),flush=True)
