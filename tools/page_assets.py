"""Predecode immutable map-page conditions; all live conditions stay live.
Offsets refer to untouched original_lcf.bin. No active page is selected here.
"""
import hashlib,json,struct
from pathlib import Path
from project_env import ROOT

def main():
 raw=(ROOT/'build/original_lcf.bin').read_bytes()
 def num(at,end):
  n=0
  for _ in range(5):
   assert at<end;b=raw[at];at+=1;n=(n<<7)|(b&127)
   if not b&128:return n,at
  raise ValueError('invalid source VLQ')
 def string(at,end):
  n,at=num(at,end);assert at+n<=end;return(at,at+n),at+n
 def fields(at,end):
  values={}
  while at<end:
   k,at=num(at,end)
   if not k:break
   values[k],at=string(at,end)
  return values,at
 def array(span):
  if not span:return []
  at,end=span;count,at=num(at,end);rows=[]
  for _ in range(count):
   key,at=num(at,end);begin=at;value,at=fields(at,end);rows.append((key,value,begin,at-begin))
  return rows
 def val(values,key,default):return num(*values[key])[0]if key in values else default
 events=[];pages=[];orders=[]
 for i in range(struct.unpack_from('<I',raw,8)[0]):
  d=12+i*48;name=raw[d:d+32].split(b'\0',1)[0].decode()
  if not name.endswith('.lmu'):continue
  offset,size=struct.unpack_from('<II',raw,d+32);_,at=string(offset,offset+size);root,_=fields(at,offset+size);evs=array(root.get(81));orders.append({'file':name,'event_ids_sorted':all(a[0]<b[0]for a,b in zip(evs,evs[1:]))})
  for key,e,begin,size in evs:
   first=len(pages);source=array(e.get(5))
   for pid,p,pg,sizepg in source:
    c=fields(*p[2])[0]if 2 in p else{};flags=val(c,1,0);values=[pid,flags,val(c,2,1),val(c,3,1),val(c,4,1),val(c,6,1),val(c,7,1),0];assert all(0<=v<=65535 for v in values)
    pages.append((pg,sizepg,val(c,5,0),val(c,8,0),*values))
   events.append((begin,size,first,len(source),0))
 slots=1
 while slots<len(events)*2:slots*=2
 table=[0]*slots;probes=[]
 for i,e in enumerate(events):
  at=e[0]*2654435761&(slots-1);n=1
  while table[at]:at=(at+1)&(slots-1);n+=1
  table[at]=i+1;probes.append(n)
 table_at=32;events_at=table_at+slots*2;pages_at=events_at+len(events)*16
 bank=struct.pack('<8I',0x44475052,1,len(raw),slots-1,table_at,events_at,pages_at,len(pages))+struct.pack('<%dH'%slots,*table)+b''.join(struct.pack('<IIIHH',*r)for r in events)+b''.join(struct.pack('<IIII8H',*r)for r in pages)
 (ROOT/'build/pages.bin').write_bytes(bank);report={'format':'immutable page spans and condition operands only; variables, switches, items, party and timer evaluated live','events':len(events),'pages':len(pages),'bytes':len(bank),'mean_lookup_probes':sum(probes)/len(probes),'original_pack_sha256':hashlib.sha256(raw).hexdigest(),'bank_sha256':hashlib.sha256(bank).hexdigest(),'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'event_array_order':orders};(ROOT/'build/pages_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='event_array_order'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
