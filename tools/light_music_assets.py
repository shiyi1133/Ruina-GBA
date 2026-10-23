"""Compile original scores with deliberately simplified gameplay timbres.

No note, controller, tempo or loop event is removed. The music room uses the
same score and a finer wavetable/stereo mix; gameplay uses a coarser mono mix.
Original SoundFont samples are the source for the small periodic timbres and
percussion. The original inputs and previous full synthesizer remain intact.
"""
import hashlib,json,math,struct,zipfile
from pathlib import Path
import numpy as np
from project_env import ROOT,ARCHIVE
from native_music_assets import sf_samples,logical,hash_name

def vlq(n):
 assert 0<=n<=0xffffffff
 out=bytearray()
 while n>=128:out.append((n&127)|128);n>>=7
 out.append(n);return out

def decode_score(data):
 """Independent encoder round-trip oracle, returning absolute source times."""
 at=32;time=0;result=[]
 def number():
  nonlocal at
  value=0;shift=0
  while True:
   b=data[at];at+=1;value|=(b&127)<<shift
   if not b&128:return value
   shift+=7;assert shift<35
 while at<len(data):
  time+=number();tag=data[at];at+=1;kind=tag&15;ch=tag>>4
  if kind==1:values=list(data[at:at+3]);at+=3
  elif kind in(2,6):values=[data[at]];at+=1
  elif kind in(3,4,5):
   v=number();values=[(v>>1)^-(v&1)]if kind==5 else[v]
  else:values=[]
  result.append([time,kind,ch,*values])
 return result

def main():
 out=ROOT/'build/light_music';out.mkdir(parents=True,exist_ok=True)
 old=json.loads((ROOT/'build/audio_manifest.json').read_text())
 oldbank=(ROOT/'build/audio.bin').read_bytes();olddata=8+28*len(old['tracks'])
 metadata=json.loads((ROOT/'build/native_soundfont_metadata.json').read_text())['presets']
 sf=ROOT/'build/audio_source/easyrpg.soundfont';raw=np.frombuffer(sf_samples(sf.read_bytes()),dtype='<i2')
 melodic=bytearray();drums=bytearray();drum_table=[];wave_notes=[]
 def normalized(samples):
  a=np.asarray(samples,dtype=np.float64);a-=a.mean()
  peak=max(1,float(np.max(np.abs(a))));return np.clip(np.rint(a*110/peak),-127,127).astype(np.int8).tobytes()
 for program in range(128):
  preset=next(p for p in metadata if p['bank']==0 and p['program']==program)
  candidates=[r for r in preset['regions']if r['low_key']<=60<=r['high_key']and r['low_vel']<=100<=r['high_vel']]
  r=max(candidates or preset['regions'],key=lambda r:bool(r['loop_mode']))
  if r['loop_mode']and r['loop_end']>r['loop_start']:
   section=raw[r['loop_start']:r['loop_end']+1].astype(float)
  else:
   start=min(r['end']-32,r['offset']+int(r['sample_rate']*.05));section=raw[start:r['end']].astype(float)
  expected=max(4,round(r['sample_rate']/(440*2**((r['keycenter']-69)/12))))
  # Choose a nearby repeating period, rather than treating an entire SF2 loop
  # (which can contain many periods) as the fundamental cycle.
  candidates=range(max(4,int(expected*.94)),max(5,int(expected*1.06)+1))
  window=section[:min(len(section),expected*12)]
  choices=[]
  for period in candidates:
   if len(window)>period*2:
    a=window[:-period];b=window[period:];den=math.sqrt(float(a@a)*float(b@b))
    choices.append((float(a@b)/den if den else 0,period))
  period=max(choices)[1]if choices else min(expected,len(section))
  if period<2:section=np.asarray([0.,1.,0.,-1.]);period=4
  cycle=section[:period];x=np.arange(256)*period/256
  values=np.interp(x,np.arange(period+1),np.r_[cycle,cycle[0]])
  melodic.extend(normalized(values));wave_notes.append({'program':program,'source_region':r['id'],'period':period})
 drum_preset=next(p for p in metadata if p['bank']==128 and p['program']==0)
 for key in range(128):
  regions=[r for r in drum_preset['regions']if r['low_key']<=key<=r['high_key']and r['low_vel']<=100<=r['high_vel']]
  if not regions:drum_table.append((0,0));continue
  r=regions[0];step=r['sample_rate']/8192*2**(((key+r['transpose']+r['tune']/100-r['keycenter'])*r['keytrack']/100)/12)
  count=min(8192,max(1,int((r['end']-r['offset'])/step)))
  phase=np.arange(count)*step+r['offset'];a=np.floor(phase).astype(int);fraction=phase-a
  values=raw[a].astype(float)*(1-fraction)+raw[np.minimum(a+1,len(raw)-1)].astype(float)*fraction
  # Keep the original one-shot's onset and amplitude envelope. Normalization
  # does not remove its release tail or create an invented percussion pattern.
  peak=max(1,float(np.max(np.abs(values))));encoded=np.clip(np.rint(values*110/peak),-127,127).astype(np.int8).tobytes()
  drum_table.append((len(drums),len(encoded)));drums.extend(encoded)
 header=32;wave_at=header;table_at=wave_at+len(melodic);pcm_at=table_at+128*8;pitch_at=(pcm_at+len(drums)+3)&~3
 bank=struct.pack('<8I',0x3146534c,1,128,wave_at,table_at,pcm_at,pitch_at,16384)+melodic+b''.join(struct.pack('<2I',*v)for v in drum_table)+drums
 bank+=bytes(pitch_at-len(bank));bank+=struct.pack('<128I',*[round(440*2**((key-69)/12)*256*65536/16384)for key in range(128)])
 (out/'native_soundfont.bin').write_bytes(bank)
 compiled={};records=[]
 native=json.loads((ROOT/'build/native_music/manifest.json').read_text())
 for track in native['tracks']:
  path=ROOT/'build/native_music'/track['file'].replace('.sequence','.events.json');music=json.loads(path.read_text())
  score=bytearray();previous=0;expected=[]
  for event in music['events']:
   at,kind,ch=event[:3];score.extend(vlq(at-previous));previous=at;score.append(kind|(ch<<4))
   if kind==1:
    key,velocity,preset=event[3:];p=metadata[preset];program=p['program']|(128 if p['bank']==128 else 0)
    score.extend((key,velocity,program));values=[key,velocity,program]
   elif kind in(2,6):score.append(event[3]);values=[event[3]]
   elif kind in(3,4,5):
    value=event[3];score.extend(vlq((value<<1)^(value>>31)if kind==5 else value));values=[value]
   else:values=[]
   expected.append([at,kind,ch,*values])
  encoded=struct.pack('<8I',0x314d534c,1,music['frames'],music['loop'],len(score),len(expected),16384,0)+score
  assert decode_score(encoded)==expected
  filename=f'{hash_name(track["name"]):08x}.sequence';(out/filename).write_bytes(encoded);compiled[track['name']]=encoded
  records.append(track|{'file':filename,'bytes':len(encoded),'score_roundtrip':'all original event timestamps and operands preserved; GM timbre variants intentionally simplified'})
 payload=bytearray();index=[];manifest=[]
 for oldtrack in old['tracks']:
  payload.extend(bytes((-len(payload))%4));offset=len(payload);name=oldtrack['name']
  if oldtrack['kind']=='music'and name in compiled:
   item=next(t for t in records if t['name']==name);data=compiled[name];kind=2;codec=0;frames=item['frames'];loop=item['loop_frame'];states=((0,0),(0,0));item=item|{'codec':'simplified original MIDI score'}
  else:
   r=struct.unpack_from('<5IhhBBH',oldbank,8+(oldtrack['id']-1)*28);codec=r[9];data=oldbank[olddata+r[2]:olddata+r[2]+r[3]*(2 if codec==2 else 1)];kind=1 if oldtrack['kind']=='sound'else 0;frames=r[3];loop=r[4];states=oldtrack['loop_states'];item=oldtrack
  payload.extend(data);(lp,li),(rp,ri)=states
  index.append((hash_name(name),kind,offset,frames,loop,lp,rp,li,ri,codec))
  manifest.append(item|{'id':len(index),'kind':'sound'if kind==1 else'music','frames':frames,'loop_frame':loop,'loop_states':states,'sample_rate':16384})
 audio=struct.pack('<II',0x41554952,len(index))+b''.join(struct.pack('<5IhhBBH',*r)for r in index)+payload
 (out/'audio.bin').write_bytes(audio)
 report={'format':'Original score events with two simplified wavetable presentation levels; unchanged source SFX',
         'music_tracks':sum(t['kind']=='music'for t in manifest),'sound_effects':sum(t['kind']=='sound'for t in manifest),
         'bytes':len(audio),'native_soundfont_bytes':len(bank),'tracks':manifest,'melodic_sources':wave_notes,
         'score_events_preserved':True,'full_original_timbre':False,'direct_pcm_wav':bool(old.get('direct_pcm_wav')),'gameplay':'coarse mono wavetable, paired samples',
         'music_room':'fine stereo wavetable, original controllers','generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
         'original_soundfont_sha256':hashlib.sha256(sf.read_bytes()).hexdigest()}
 (out/'audio_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in report.items()if k not in('tracks','melodic_sources')},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
