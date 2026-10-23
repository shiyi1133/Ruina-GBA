"""Extract original MIDI tempo maps for the event 'MIDI play position' operand.
Audio remains the previously converted original tracks; no notes are changed.
"""
import hashlib,json,struct,zipfile
from fractions import Fraction
from pathlib import Path
from project_env import ROOT,ARCHIVE

def tempo_map(data):
 assert data[:4]==b'MThd';n=struct.unpack_from('>I',data,4)[0];division=struct.unpack_from('>H',data,12)[0];assert division and not division&0x8000
 offset=8+n;tempos=[]
 while offset<len(data):
  tag=data[offset:offset+4];length=struct.unpack_from('>I',data,offset+4)[0];track=data[offset+8:offset+8+length];offset+=8+length
  if tag!=b'MTrk':continue
  at=0;tick=0;status=0
  def vlq():
   nonlocal at
   value=0
   while True:
    b=track[at];at+=1;value=(value<<7)|(b&127)
    if not b&128:return value
  while at<len(track):
   tick+=vlq();b=track[at]
   if b&128:status=b;at+=1
   if status==255:
    kind=track[at];at+=1;length=vlq();blob=track[at:at+length];at+=length
    if kind==81 and length==3:tempos.append((tick,int.from_bytes(blob,'big')))
   elif status in (240,247):
    length=vlq();at+=length
   elif status&240 in (192,208):at+=1
   else:at+=2
 segments=[{'tick':0,'sample':0,'tempo':500000,'division':division}];previous_tick=0;tempo=500000;us=Fraction(0)
 for tick,value in sorted(tempos):
  us+=(tick-previous_tick)*Fraction(tempo,division);previous_tick=tick;tempo=value
  row={'tick':tick,'sample':int(us*16384/1000000),'tempo':tempo,'division':division}
  if segments[-1]['tick']==tick:segments[-1]=row
  else:segments.append(row)
 return segments

def main():
 manifest=json.loads((ROOT/'build/audio_manifest.json').read_text());rows=[]
 for track in manifest['tracks']:
  if track['kind']!='music'or not track['source'].lower().endswith('.mid'):continue
  cached=ROOT/'build/audio_cache'/('0_%08x.mid'%hash_name(track['name']))
  if not cached.exists():
   with zipfile.ZipFile(ARCHIVE)as archive:data=archive.read(track['source'])
   cached.write_bytes(data)
  data=cached.read_bytes();assert hashlib.sha256(data).hexdigest()==track['source_sha256']
  rows.append({'id':track['id'],'source':track['source'],'sha256':track['source_sha256'],'segments':tempo_map(data)})
 lines=['/* Original MIDI tempo maps, generated without changing source music. */','#include "types.h"','typedef struct {u32 sample,tick,tempo,division;} MidiTempo;']
 for row in rows:
  lines.append('static const MidiTempo midi_%d[]={%s};'%(row['id'],','.join('{%d,%d,%d,%d}'%(s['sample'],s['tick'],s['tempo'],s['division'])for s in row['segments'])))
 lines+=['int midi_clock_ticks(int id,u32 sample){const MidiTempo*p=0;unsigned count=0,i;switch(id){']
 for row in rows:lines.append('case %d:p=midi_%d;count=sizeof(midi_%d)/sizeof(MidiTempo);break;'%(row['id'],row['id'],row['id']))
 lines+=['default:return 0;}for(i=1;i<count&&p[i].sample<=sample;i++){}p+=i-1;return p->tick+(int)((unsigned long long)(sample-p->sample)*1000000*p->division/(16384ULL*p->tempo));}','']
 (ROOT/'build/midi_clock.c').write_text('\n'.join(lines));(ROOT/'build/midi_clock_manifest.json').write_text(json.dumps({'kind':'original MIDI tempo/tick mapping at 16384 source samples per second','tracks':rows},ensure_ascii=False,indent=2))
 print(json.dumps({'MIDI_clock_tracks':len(rows),'tempo_segments':sum(len(r['segments'])for r in rows)}))
def hash_name(name):
 h=2166136261
 for b in name.encode('cp932'):h=((h^b)*16777619)&0xffffffff
 return h
if __name__=='__main__':main()
