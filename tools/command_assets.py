"""Predecode immutable transport for parallel pages and statically called commons.
No condition, variable, RNG, wait or control-flow decision is evaluated here.
All dynamic execution continues to use the unchanged original bytecode spans.
The bank uses original-pack byte offsets, never build-dependent pointers.
"""
import hashlib,json,struct
from pathlib import Path
from project_env import ROOT

def main():
 raw=(ROOT/'build/original_lcf.bin').read_bytes()
 def num(at,end):
  value=0
  for _ in range(5):
   assert at<end;b=raw[at];at+=1;value=(value<<7)|(b&127)
   if not b&128:return value,at
  raise ValueError('invalid source VLQ')
 def string(at,end):
  n,at=num(at,end);assert at+n<=end;return(at,at+n),at+n
 def fields(at,end):
  values={}
  while at<end:
   key,at=num(at,end)
   if not key:break
   values[key],at=string(at,end)
  return values,at
 def array(span):
  if span is None:return []
  at,end=span;count,at=num(at,end);result=[]
  for _ in range(count):
   key,at=num(at,end);value,at=fields(at,end);result.append((key,value))
  return result
 def integer(span,default=0):return num(*span)[0]if span else default
 def commands(span):
  if span is None:return []
  at,end=span;result=[]
  while at<end:
   start=at;code,at=num(at,end);indent,at=num(at,end);text,at=string(at,end);count,at=num(at,end);parameters=at;values=[]
   for _ in range(count):value,at=num(at,end);values.append(value)
   result.append({'offset':start,'advance':at-start,'code':code,'indent':indent,'text_offset':text[0],'text_size':text[1]-text[0],'parameter_size':at-parameters,'values':values})
  return result
 commons={};common_fields={};parallel=[];seeds=set()
 for i in range(struct.unpack_from('<I',raw,8)[0]):
  d=12+i*48;name=raw[d:d+32].split(b'\0',1)[0].decode();offset,size=struct.unpack_from('<II',raw,d+32);_,at=string(offset,offset+size);root,_=fields(at,offset+size)
  if name.endswith('.ldb'):
   common_fields=dict(array(root.get(25)));commons={key:commands(value.get(22))for key,value in common_fields.items()}
  elif name.endswith('.lmu'):
   for _,event in array(root.get(81)):
    for _,page in array(event.get(5)):
     if integer(page.get(33))==4:parallel.extend(commands(page.get(52)))
 def callees(rows):return {r['values'][1]for r in rows if r['code']==12330 and len(r['values'])>1 and r['values'][0]==0}
 seeds.update(key for key,value in common_fields.items()if integer(value.get(11))==4);seeds.update(callees(parallel));seen=set();pending=list(seeds)
 while pending:
  key=pending.pop()
  if key in seen or key not in commons:continue
  seen.add(key);pending.extend(callees(commons[key]))
 all_rows=parallel+[r for key in sorted(seen)for r in commons[key]];eligible={r['offset']:r for r in all_rows if len(r['values'])<=8 and all(r[k]<=65535 for k in('advance','code','indent','text_size','parameter_size'))}
 rows=[eligible[key]for key in sorted(eligible)];slots=1
 while slots<len(rows)*2:slots*=2
 assert len(rows)<65535;indices=[0]*slots;probes=[]
 for i,r in enumerate(rows):
  at=((r['offset']*2654435761)&0xffffffff)&(slots-1);n=0
  while indices[at]:at=(at+1)&(slots-1);n+=1
  indices[at]=i+1;probes.append(n+1)
 table=32;records=(table+slots*2+3)&~3;bank=bytearray(struct.pack('<8I',0x444d4350,1,len(raw),slots-1,table,records,len(rows),52));bank.extend(struct.pack('<%dH'%slots,*indices));bank.extend(bytes(records-len(bank)))
 for r in rows:
  bank.extend(struct.pack('<IHHHHIHH8I',r['offset'],r['advance'],r['code'],r['indent'],r['text_size'],r['text_offset'],r['parameter_size'],len(r['values']),*(r['values']+[0]*(8-len(r['values'])))))
 target=ROOT/'build/commands.bin';target.write_bytes(bank)
 report={'format':'immutable command transport only; dynamic conditions and original VM remain live','target_commands':len(all_rows),'cached_commands':len(rows),'common_ids':sorted(seen),'bytes':len(bank),'hash_slots':slots,'max_lookup_probes':max(probes),'mean_lookup_probes':sum(probes)/len(probes),'original_pack_sha256':hashlib.sha256(raw).hexdigest(),'bank_sha256':hashlib.sha256(bank).hexdigest(),'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(ROOT/'build/commands_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
