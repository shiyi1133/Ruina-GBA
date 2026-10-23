"""Convert complete original tracks and effects for GBA Direct Sound.

MIDI keeps the supplied SoundFont, programs, drum channel, tempo events and
CC111 loop point. Stereo IMA ADPCM is a storage conversion, not new music.
"""
from pathlib import Path
import audioop,hashlib,io,json,struct,subprocess,sys,wave,zipfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build';CACHE=OUT/'audio_cache';CACHE.mkdir(exist_ok=True)
from project_env import ARCHIVE as ZIP
z=zipfile.ZipFile(ZIP)
def logical(n):
 try:return n.encode('gbk').decode('cp932')
 except UnicodeError:return n
names={logical(n):n for n in z.namelist()}
def hash_name(n):
 h=2166136261
 for v in n.encode('cp932'):h=((h^v)*16777619)&0xffffffff
 return h
tracks=['scene19','ダンジョン4','町1','Tale','battle10','boss12','J戦闘終了1','ゲームオーバー3','J宿2','安らぎ3','店2','船1','船2','乗り物1','boss05']
sf=OUT/'audio_source/easyrpg.soundfont';renderer=OUT/'render_midi'
subprocess.run(['cc','-O2',str(ROOT/'tools/render_midi.c'),'-lm','-o',str(renderer)],check=True)
renderer_sha=hashlib.sha256((ROOT/'tools/render_midi.c').read_bytes()+sf.read_bytes()).hexdigest()
blobs=[];entries=[];manifest=[]
for kind,resources in [(0,['Ruina121/game/Music/'+n+'.mid'for n in tracks]),(1,sorted(n for n in names if '/Sound/'in n and n.lower().endswith('.wav')))]:
 for key in resources:
  name=Path(key).stem;source=z.read(names[key]);digest=hashlib.sha256(source).hexdigest();cache=CACHE/(f'{kind}_{hash_name(name):08x}');meta_path=cache.with_suffix('.json');encoded_path=cache.with_suffix('.adpcm')
  meta=json.loads(meta_path.read_text())if meta_path.exists()else{}
  signature=digest+renderer_sha+'stereo-ima-v1'
  if meta.get('signature')!=signature or not encoded_path.exists():
   if kind==0:
    mid=cache.with_suffix('.mid');mid.write_bytes(source);timing=json.loads(subprocess.check_output([str(renderer),str(sf),str(mid)]));pcmfile=cache.with_suffix('.pcm16');subprocess.run([str(renderer),str(sf),str(mid),str(pcmfile)],check=True);pcm=pcmfile.read_bytes();loop=timing['loop_ms']*16384//1000
   else:
    w=wave.open(io.BytesIO(source));pcm=w.readframes(w.getnframes());width=w.getsampwidth();ch=w.getnchannels();rate=w.getframerate()
    if width==1:pcm=audioop.bias(pcm,1,-128)
    if width!=2:pcm=audioop.lin2lin(pcm,width,2)
    if rate!=16384:pcm,_=audioop.ratecv(pcm,2,ch,rate,16384,None)
    if ch==1:pcm=audioop.tostereo(pcm,2,1,1)
    loop=0xffffffff;timing={}
   frames=len(pcm)//4;frames&=~1;pcm=pcm[:frames*4];loop=loop&~1 if loop<frames else 0xffffffff
   left=audioop.tomono(pcm,2,1,0);right=audioop.tomono(pcm,2,0,1);codes=[];loopstates=[]
   for channel in [left,right]:
    if loop!=0xffffffff:
     first,st=audioop.lin2adpcm(channel[:loop*2],2,(0,0));rest,end=audioop.lin2adpcm(channel[loop*2:],2,st);codes.append(np.frombuffer(first+rest,dtype=np.uint8));loopstates.append(st)
    else:
     enc,end=audioop.lin2adpcm(channel,2,(0,0));codes.append(np.frombuffer(enc,dtype=np.uint8));loopstates.append((0,0))
   encoded=np.empty(frames,np.uint8);encoded[::2]=(codes[0]&240)|(codes[1]>>4);encoded[1::2]=(codes[0]<<4)|(codes[1]&15);encoded_path.write_bytes(encoded.tobytes())
   meta={'signature':signature,'source':key,'source_sha256':digest,'frames':frames,'loop_frame':loop,'loop_states':loopstates,'sample_rate':16384,'timing':timing};meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2))
   print('AUDIO_CONVERT',name,round(meta['frames']/16384,3),flush=True)
  blob=encoded_path.read_bytes();offset=sum(len(b)for b in blobs);offset=(offset+3)&~3
  if blobs:blobs.append(bytes(offset-sum(len(b)for b in blobs)))
  (pl,il),(pr,ir)=meta['loop_states'];entries.append((hash_name(name),kind,offset,meta['frames'],meta['loop_frame'],pl,pr,il,ir));blobs.append(blob);manifest.append(meta|{'name':name,'id':len(entries),'kind':'music'if kind==0 else 'sound'})
# Offsets are relative to PCM section after the fixed index.
index=struct.pack('<II',0x41554952,len(entries))+b''.join(struct.pack('<5IhhBBH',*e,0)for e in entries)
(OUT/'audio.bin').write_bytes(index+b''.join(blobs));(OUT/'audio_manifest.json').write_text(json.dumps({'format':'stereo IMA, one sample frame per byte, 16384 Hz','renderer':'TinySoundFont using supplied easyrpg.soundfont','tracks':manifest,'bytes':len(index)+sum(map(len,blobs))},ensure_ascii=False,indent=2));print('AUDIO_PACK',len(entries),len(index)+sum(map(len,blobs)),flush=True)
