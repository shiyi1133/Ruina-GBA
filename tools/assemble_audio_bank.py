"""Assemble the candidate full soundtrack without changing a released bank.
Stable track IDs are retained. Existing validated PCM for the opening and
original sound effects is reused byte for byte; later MIDI shares SF2 samples.
"""
import audioop,hashlib,io,json,struct,wave,zipfile
import numpy as np
from native_music_assets import OUT,ROOT,ARCHIVE,logical,hash_name

def wav_track(raw,loop):
 with wave.open(io.BytesIO(raw))as w:
  pcm=w.readframes(w.getnframes());width=w.getsampwidth();channels=w.getnchannels();rate=w.getframerate()
 if width==1:pcm=audioop.bias(pcm,1,-128)
 if width!=2:pcm=audioop.lin2lin(pcm,width,2)
 if rate!=16384:pcm,_=audioop.ratecv(pcm,2,channels,rate,16384,None)
 if channels==1:pcm=audioop.tostereo(pcm,2,1,1)
 frames=(len(pcm)//4)&~1;pcm=pcm[:frames*4];codes=[]
 for channel in [audioop.tomono(pcm,2,1,0),audioop.tomono(pcm,2,0,1)]:codes.append(np.frombuffer(audioop.lin2adpcm(channel,2,(0,0))[0],dtype=np.uint8))
 encoded=np.empty(frames,np.uint8);encoded[::2]=(codes[0]&240)|(codes[1]>>4);encoded[1::2]=(codes[0]<<4)|(codes[1]&15)
 return encoded.tobytes(),frames,0 if loop else 0xffffffff

def main():
 original=ROOT/'history/pre_full_audio_20261021';old=json.loads((original/'audio_manifest.json').read_text());old_bytes=(original/'audio.bin').read_bytes();old_data=8+28*len(old['tracks'])
 native=json.loads((OUT/'manifest.json').read_text());native_by_name={t['name']:t for t in native['tracks']}
 keep_pcm={'scene19','ダンジョン4','町1','Tale'}
 records=[];manifest=[];payload=bytearray();used=set();cache=ROOT/'build/audio_cache'
 def add(t,kind,data,frames,loop,states=((0,0),(0,0))):
  padding=bytes((-len(payload))%4);payload.extend(padding);offset=len(payload);payload.extend(data)
  (lp,li),(rp,ri)=states
  records.append((hash_name(t['name']),kind,offset,frames,loop,lp,rp,li,ri,0))
  if kind!=1:used.add(t['name'])
  manifest.append(t|{'id':len(records),'frames':frames,'loop_frame':loop,'kind':'sound'if kind==1 else 'music','codec':'native MIDI/SF2'if kind==2 else 'stereo IMA','loop_states':states,'sample_rate':16384})
 for t in old['tracks']:
  if t['kind']=='music'and t['name']not in keep_pcm:
   nt=native_by_name[t['name']];add(nt,2,(OUT/nt['file']).read_bytes(),nt['frames'],nt['loop_frame'])
  else:
   entry=struct.unpack_from('<5IhhBBH',old_bytes,8+(t['id']-1)*28);start=old_data+entry[2];add(t,0 if t['kind']=='music'else 1,old_bytes[start:start+entry[3]],entry[3],entry[4],t['loop_states'])
 for t in native['tracks']:
  (cache/('0_%08x.mid'%hash_name(t['name']))).write_bytes((OUT/t['file'].replace('.sequence','.mid')).read_bytes())
  if t['name']not in used:add(t,2,(OUT/t['file']).read_bytes(),t['frames'],t['loop_frame'])
 with zipfile.ZipFile(ARCHIVE)as z:
  sources={logical(n):n for n in z.namelist()}
  for path in sorted(n for n in sources if '/Music/'in n and n.lower().endswith('.wav')):
   raw=z.read(sources[path]);data,frames,loop=wav_track(raw,True);t={'name':path.rsplit('/',1)[1][:-4],'source':path,'source_sha256':hashlib.sha256(raw).hexdigest()};add(t,0,data,frames,loop)
 bank=struct.pack('<II',0x41554952,len(records))+b''.join(struct.pack('<5IhhBBH',*r)for r in records)+payload
 (OUT/'audio.bin').write_bytes(bank);report={'format':'Stereo IMA PCM + native original MIDI/SF2','renderer':'Original supplied SoundFont; fixed point native synthesis for later MIDI','tracks':manifest,'bytes':len(bank),'native_soundfont_bytes':(OUT/'native_soundfont.bin').stat().st_size,'music_tracks':sum(t['kind']=='music'for t in manifest),'sound_effects':sum(t['kind']=='sound'for t in manifest)}
 (OUT/'audio_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='tracks'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
