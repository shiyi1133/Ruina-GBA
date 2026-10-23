"""Compile original MIDI scores and the supplied SoundFont into shared ROM data.

This candidate bank is kept separate until native playback has passed checks.
The GBA never parses SF2, allocates a synthesizer heap, or uses floating point.
"""
import hashlib,json,math,struct,subprocess,zipfile
from pathlib import Path
from project_env import ROOT,ARCHIVE

OUT=ROOT/'build/native_music';OUT.mkdir(parents=True,exist_ok=True)
RATE=16384;Q=1<<24

def logical(n):
 try:return n.encode('gbk').decode('cp932')
 except UnicodeError:return n

def hash_name(n):
 h=2166136261
 for c in n.encode('cp932'):h=((h^c)*16777619)&0xffffffff
 return h

def envelope(e,key,amp):
 hold=e['hold'];decay=e['decay']
 if e['key_hold']:
  hold+=e['key_hold']*(60-key);hold=0 if hold < -10000 else 2**(hold/1200)
 if e['key_decay']:
  decay+=e['key_decay']*(60-key);decay=0 if decay < -10000 else 2**(decay/1200)
 delay=int(e['delay']*RATE);attack=int(e['attack']*RATE);hold=int(hold*RATE);decay=int(decay*RATE)
 release=int((e['release'] if e['release']>0 else .01)*RATE);sustain=e['sustain']
 if amp:
  coefficient=round(math.exp(-9.226/max(1,decay))*(1<<30));length=int(math.log(sustain)/(-9.226/max(1,decay))) if sustain>0 else decay
 else:coefficient=0;length=int(decay*(1-sustain))
 return [delay,attack,hold,decay,release,round(sustain*Q),coefficient,round(math.exp(-9.226/max(1,release))*(1<<30)),length]

def tone_bytes(region,key,preset,sample_pack,pre_resample=False):
 r=region
 # No active SF2 lowpass in the original font at this output rate. Fail rather
 # than silently omit a newly supplied font's filter or unsupported LFO.
 assert r['filter_fc']==13500 and not r['mod_lfo_filter'] and not r['mod_env_filter'] and not r['vib_lfo_pitch']
 note=key+r['transpose']+r['tune']/100
 semitones=(note-r['keycenter'])*r['keytrack']/100
 step=round(r['sample_rate']/RATE*2**(semitones/12)*65536)
 loop=r['loop_mode'] and r['loop_start']<r['loop_end'];assert r['loop_mode'] in (0,1)
 offset,end,loop_start,loop_end,step=sample_pack(r,step,loop,pre_resample)
 values=[offset,end,loop_start,loop_end,step,round(10**((-6-r['attenuation'])/20)*65536),round(r['pan']*32768),r['group'],preset,r['mod_lfo_pitch'],round(r['mod_lfo_volume']),r['mod_env_pitch'],0,int(r['mod_lfo_delay']*RATE),round(4*8.176*2**(r['mod_lfo_frequency']/1200)/RATE*Q)]
 return struct.pack('<6Ii2H4h2I',*values)+struct.pack('<18I',*(envelope(r['amp'],key,True)+envelope(r['mod'],key,False)))

def sf_samples(data):
 assert data[:4]==b'RIFF' and data[8:12]==b'sfbk'
 at=12
 while at<len(data):
  size=struct.unpack_from('<I',data,at+4)[0]
  if data[at:at+4]==b'LIST' and data[at+8:at+12]==b'sdta':
   p=at+12
   while p<at+8+size:
    n=struct.unpack_from('<I',data,p+4)[0]
    if data[p:p+4]==b'smpl':return data[p+8:p+8+n]
    p+=8+n+(n&1)
  at+=8+size+(size&1)
 raise ValueError('Original SoundFont has no PCM samples')

def main():
 sf=ROOT/'build/audio_source/easyrpg.soundfont'
 export=OUT/'export_midi_events';subprocess.run(['cc','-O2',str(ROOT/'tools/export_midi_events.c'),'-lm','-o',str(export)],check=True)
 metadata=ROOT/'build/native_soundfont_metadata.json'
 subprocess.run(['cc','-O2',str(ROOT/'tools/export_soundfont.c'),'-lm','-o',str(OUT/'export_soundfont')],check=True)
 metadata.write_bytes(subprocess.check_output([str(OUT/'export_soundfont'),str(sf)]))
 import numpy as np
 presets=json.loads(metadata.read_text())['presets'];tones=[];tone_ids={};lists=bytearray();list_ids={};tracks=[];loop_ids={};loop_ranges=[]
 raw_samples=np.frombuffer(sf_samples(sf.read_bytes()),dtype='<i2');sample_bank=bytearray();sample_ids={};resampled_count=0
 def sample_pack(r,step,loop,pre_resample):
  nonlocal resampled_count
  identity=(r['offset'],r['end'],step if pre_resample else 0,r['loop_start']if loop else 0,r['loop_end']if loop else 0)
  if identity not in sample_ids:
   start=len(sample_bank)//2;length=r['end']-r['offset']
   if pre_resample:
    count=(length*65536+step-1)//step;phase=np.arange(count,dtype=np.int64)*step;pos=r['offset']+(phase>>16);fraction=phase&65535
    a=raw_samples[pos].astype(np.int64);b=raw_samples[pos+1].astype(np.int64)
    data=(a+(((b-a)*fraction)>>16)).astype('<i2').tobytes()+bytes(2);length=count;resampled_count+=1
   else:
    data=bytearray(raw_samples[r['offset']:r['end']+1].tobytes())
    if loop:
     # The next interpolation sample at a loop boundary is its first sample.
     # Materialize that exact guard offline to remove an ARM7 branch per sample.
     struct.pack_into('<h',data,(r['loop_end']+1-r['offset'])*2,int(raw_samples[r['loop_start']]))
   sample_bank.extend(data);sample_ids[identity]=(start,start+length)
  start,end=sample_ids[identity]
  return start,end,start+r['loop_start']-r['offset'] if loop else 0,start+r['loop_end']-r['offset'] if loop else 0,65536 if pre_resample else step
 source_signature=hashlib.sha256((ROOT/'tools/export_midi_events.c').read_bytes()+sf.read_bytes()).hexdigest()
 with zipfile.ZipFile(ARCHIVE)as z:
  sources={logical(n):n for n in z.namelist()}
  for path in sorted(n for n in sources if '/Music/'in n and n.lower().endswith('.mid')):
   name=Path(path).stem;raw=z.read(sources[path]);cache=OUT/('%08x.mid'%hash_name(name));cache.write_bytes(raw)
   cached=cache.with_suffix('.events.json');signature=cache.with_suffix('.sha256');digest=hashlib.sha256(raw).hexdigest()+source_signature
   if not cached.exists() or not signature.exists() or signature.read_text()!=digest:
    cached.write_bytes(subprocess.check_output([str(export),str(sf),str(cache)]));signature.write_text(digest)
   music=json.loads(cached.read_text());encoded=bytearray();note_count=0;layers=0;unmapped=[];loop_offset=None;loop_usage={}
   bent_channels={e[2]for e in music['events']if e[1]==4 and e[3]!=1048576}
   for event in music['events']:
    at,kind,ch=event[:3]
    if loop_offset is None and at>=music['loop']:loop_offset=len(encoded)
    if kind==1:
     key,velocity,preset=event[3:];ids=[];note_count+=1
     for region in presets[preset]['regions']:
      if not(region['low_key']<=key<=region['high_key'] and region['low_vel']<=velocity<=region['high_vel']):continue
      fast=not region['loop_mode'] and not region['mod_lfo_pitch'] and not region['mod_env_pitch'] and ch not in bent_channels
      identity=(region['id'],key,fast)
      if identity not in tone_ids:
       tone_ids[identity]=len(tones);tone=bytearray(tone_bytes(region,key,preset,sample_pack,fast));ls,le=struct.unpack_from('<2I',tone,8)
       if ls<le:
        if (ls,le)not in loop_ids:loop_ids[ls,le]=len(loop_ranges);loop_ranges.append((ls,le))
        struct.pack_into('<h',tone,38,loop_ids[ls,le]+1)
       tones.append(tone)
      tid=tone_ids[identity];ids.append(tid);lid=struct.unpack_from('<h',tones[tid],38)[0]-1
      if lid>=0:loop_usage[lid]=loop_usage.get(lid,0)+1
     if not ids:unmapped.append([at,ch,key,velocity,preset])
     identity=tuple(ids);layers+=len(ids)
     if identity not in list_ids:
      list_ids[identity]=len(lists);lists.extend(struct.pack('<H',len(ids))+struct.pack('<%dH'%len(ids),*ids))
     encoded.extend(struct.pack('<III',at,kind|(ch<<4)|(key<<8)|(velocity<<16),list_ids[identity]))
    elif kind in (3,4,5):encoded.extend(struct.pack('<IIi',at,kind|(ch<<4),event[3]))
    else:encoded.extend(struct.pack('<II',at,kind|(ch<<4)|(event[3]<<8)))
   cache_descriptors=[];cache_samples=0;cached_notes=0
   for lid,count in sorted(loop_usage.items(),key=lambda v:v[1]/(loop_ranges[v[0]][1]-loop_ranges[v[0]][0]+2),reverse=True):
    ls,le=loop_ranges[lid];length=le-ls+2
    if cache_samples+length<=2048:
     cache_descriptors.append((lid,ls,cache_samples,length));cache_samples+=length;cached_notes+=count
   encoded=struct.pack('<6I',len(encoded),music['frames'],music['loop'],loop_offset or 0,24,len(cache_descriptors))+b''.join(struct.pack('<4I',*d)for d in cache_descriptors)+encoded
   file=OUT/('%08x.sequence'%hash_name(name));file.write_bytes(encoded)
   tracks.append({'name':name,'source':path,'source_sha256':hashlib.sha256(raw).hexdigest(),'frames':music['frames'],'loop_frame':music['loop'],'file':file.name,'event_count':len(music['events']),'note_count':note_count,'sample_layers':layers,'cached_loop_samples':cache_samples,'cached_loop_notes':cached_notes,'total_loop_notes':sum(loop_usage.values()),'bytes':len(encoded),'unmapped_notes':unmapped})
 assert len(tones)<65536 and len(loop_ids)<=512
 chunks=[];offset=44
 def add(data):
  nonlocal offset
  start=offset;chunks.append(data);offset+=len(data);padding=bytes((-offset)%4);chunks.append(padding);offset+=len(padding);return start
 tone_offset=add(b''.join(tones));list_offset=add(lists);samples=bytes(sample_bank);sample_offset=add(samples)
 pitch_offset=add(struct.pack('<4801I',*[round(2**(c/1200)*(1<<20))for c in range(-2400,2401)]))
 volume_offset=add(struct.pack('<401I',*[round(10**(v/2000)*65536)for v in range(-200,201)]))
 pan_offset=add(struct.pack('<4097I',*[round(math.sqrt(v/4096)*65536)for v in range(4097)]))
 # Reversible interpolation pairs save a second cartridge sample read and
 # subtraction in ARM7's hot loop. A signed-16 delta must be exact: large
 # discontinuities retain the original S16 interpolation path instead.
 pcm=np.frombuffer(samples,dtype='<i2');pair_offsets=[];pair_bytes=0;pair_fallbacks=0
 for ls,le in loop_ranges:
  a=pcm[ls:le+1].astype(np.int32);delta=pcm[ls+1:le+2].astype(np.int32)-a
  if np.any((delta< -32768)|(delta>32767)):
   pair_offsets.append(0);pair_fallbacks+=1;continue
  packed=(a.astype(np.uint32)&65535)|((delta.astype(np.uint32)&65535)<<16)
  raw=packed.astype('<u4').tobytes();pair_offsets.append(add(raw));pair_bytes+=len(raw)
 pair_offset=add(struct.pack('<%dI'%len(pair_offsets),*pair_offsets))
 header=struct.pack('<11I',0x31464d52,3,tone_offset,len(tones),list_offset,sample_offset,len(samples)//2,pitch_offset,volume_offset,pan_offset,pair_offset)
 bank=header+b''.join(chunks);(OUT/'native_soundfont.bin').write_bytes(bank)
 report={'format':'Original MIDI events plus shared original SF2 PCM, fixed point synthesis','loop_interpolation_guard':True,'exact_interpolation_pair_bytes':pair_bytes,'pair_fallback_loops':pair_fallbacks,'soundfont_sha256':hashlib.sha256(sf.read_bytes()).hexdigest(),'soundfont_sample_bytes':len(samples),'pre_resampled_fixed_pitch_one_shots':resampled_count,'tone_count':len(tones),'tone_record_bytes':len(tones[0]),'note_lists':len(list_ids),'native_bank_bytes':len(bank),'sequence_bytes':sum(t['bytes']for t in tracks),'tracks':tracks}
 (OUT/'manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='tracks'},indent=2),flush=True)
 print('UNMAPPED',sum(len(t['unmapped_notes'])for t in tracks),flush=True)

if __name__=='__main__':main()
