"""Read-only LCF data inspection. No Windows executable is run."""
from pathlib import Path
import zipfile,json,struct,zlib,collections
from project_env import ROOT,ARCHIVE as ZIP
class Reader:
 def __init__(self,b):self.b=b;self.at=0
 def num(self):
  n=0
  for _ in range(8):
   v=self.b[self.at];self.at+=1;n=(n<<7)|(v&127)
   if not(v&128):return n
  raise ValueError('Bad integer')
 def take(self,n):
  v=self.b[self.at:self.at+n];self.at+=n;assert len(v)==n;return v
 def string(self):return self.take(self.num())
 def fields(self):
  out={}
  while self.at<len(self.b):
   k=self.num()
   if k==0:break
   out[k]=self.string()
  return out
def integer(b,default=0):return Reader(b).num()if b else default
def fields(b):return Reader(b).fields()
def array(b):
 if not b:return []
 r=Reader(b);n=r.num();out=[]
 for _ in range(n):i=r.num();out.append((i,r.fields()))
 return out
def text(b):return b.decode('gbk',errors='replace')
def filename(b):return b.decode('cp932',errors='replace')
def commands(b):
 r=Reader(b);out=[]
 while r.at<len(b):
  code=r.num();indent=r.num();s=r.string();count=r.num();params=[r.num()for _ in range(count)]
  params=[x-0x100000000 if x>=0x80000000 else x for x in params]
  out.append({'code':code,'indent':indent,'text':text(s),'file':filename(s),'params':params})
 return out
def data_root(b):r=Reader(b);head=r.string();return head,r.fields()
def main():
 out=ROOT/'research';out.mkdir(exist_ok=True)
 with zipfile.ZipFile(ZIP)as z:
  db=data_root(z.read('Ruina121/game/RPG_RT.ldb'))[1]
  print('DB_FIELDS',[(k,len(v))for k,v in db.items()])
  maps=[];all_events=[]
  for info in z.infolist():
   if not info.filename.endswith('.lmu'):continue
   number=int(Path(info.filename).stem[3:]);_,m=data_root(z.read(info));events=[]
   for eid,e in array(m.get(81,b'')):
    pages=[]
    for pid,p in array(e.get(5,b'')):
     cmd=commands(p.get(52,b''));pages.append({'id':pid,'commands':cmd})
    events.append({'id':eid,'name':text(e.get(1,b'')),'x':integer(e.get(2,b'')),'y':integer(e.get(3,b'')),'pages':pages})
   entry={'id':number,'width':integer(m.get(2,b''),20),'height':integer(m.get(3,b''),15),'background':filename(m.get(32,b'')),'events':events};maps.append(entry)
   lines=[]
   for e in events:
    lines.append(f"\n=== event {e['id']} {e['name']} ({e['x']},{e['y']}) ===")
    for p in e['pages']:
     lines.append(f"PAGE {p['id']}")
     for c in p['commands']:
      if c['code']in[10110,20110,10140,20140,10710,10810,11510,11720,11110,10130,10610]:lines.append(f"{c['code']} {c['text']} {c['params']}  FILE={c['file']}")
   (out/f'map_{number:03}.txt').write_text('\n'.join(lines))
  db_tables={}
  for key,label in [(11,'actors'),(12,'skills'),(13,'items'),(14,'enemies'),(15,'troops'),(23,'switches'),(24,'variables')]:
   db_tables[label]=[{'id':i,'name':text(v.get(1,b'')),'fields':{str(k):w.hex()for k,w in v.items()}}for i,v in array(db.get(key,b''))]
  commons=[]
  for cid,c in array(db.get(25,b'')):
   cmd=commands(c.get(22,b''));commons.append({'id':cid,'name':text(c.get(1,b'')),'commands':cmd})
  (out/'database.json').write_text(json.dumps(db_tables,ensure_ascii=False,indent=2));(out/'maps.json').write_text(json.dumps(maps,ensure_ascii=False,indent=2));(out/'common_events.json').write_text(json.dumps(commons,ensure_ascii=False,indent=2))
  print('MAPS',[(m['id'],len(m['events']),m['background'])for m in maps])
if __name__=='__main__':main()
