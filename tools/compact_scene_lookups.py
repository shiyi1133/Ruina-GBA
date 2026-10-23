"""Losslessly pack scene color-index lookups; original RGB555 mappings stay exact."""
import hashlib,json,re,struct
from pathlib import Path
from project_env import ROOT

def pack(raw):
 rows=len(raw)//32;blob=bytearray(8+rows*2);struct.pack_into('<4sI',blob,0,b'SP32',len(raw));seen={}
 for row in range(rows):
  values=raw[row*32:row*32+32];runs=[];at=0
  while at<32:
   end=at+1
   while end<32 and values[end]==values[at]:end+=1
   runs.extend((end,values[at]));at=end
  encoded=bytes([len(runs)//2])+bytes(runs)if len(runs)<32 else b'\0'+values
  if encoded not in seen:seen[encoded]=len(blob);blob.extend(encoded)
  struct.pack_into('<H',blob,8+row*2,seen[encoded])
 assert len(blob)<65536;return bytes(blob)
def unpack(blob):
 assert blob[:4]==b'SP32';size=struct.unpack_from('<I',blob,4)[0];out=bytearray()
 for row in range(size//32):
  at=struct.unpack_from('<H',blob,8+row*2)[0];n=blob[at];at+=1
  if not n:out.extend(blob[at:at+32]);continue
  x=0
  for _ in range(n):end,color=blob[at:at+2];at+=2;out.extend(bytes([color])*(end-x));x=end
  assert x==32
 assert len(out)==size;return bytes(out)
def main():
 out=ROOT/'build';manifest=out/'scene_lookups_packed.json';generation=hashlib.sha256(Path(__file__).read_bytes()).hexdigest();assets=out/'assets.c';assembly=out/'high_color_blobs.s'
 if manifest.exists():
  old=json.loads(manifest.read_text())
  if old.get('generator_sha256')==generation and all((out/p).exists()and hashlib.sha256((out/p).read_bytes()).hexdigest()==h for p,h in old['cached_inputs'].items()):print(json.dumps({'scene_lookups':'cached','bytes_saved':old['bytes_saved']}));return
 source=assets.read_text();code=assembly.read_text();bits={name:int(value)for name,value in re.findall(r'\{[^,{}]+,(scene_nearest_\d+),[^,{}]+,(\d+),',source)};blob=bytearray();records=[]
 pattern=r'(\.global (scene_nearest_\d+)\n\2:\n)\.incbin "(build/[^"\n]+)",(\d+),(\d+)'
 def replace(m):
  name,path,at,size=m[2],m[3],int(m[4]),int(m[5]);data=(ROOT/path).read_bytes()[at:at+size];raw=unpack(data)if bits[name]&128 else data;encoded=pack(raw);assert unpack(encoded)==raw
  blob.extend(bytes((-len(blob))%4));offset=len(blob);blob.extend(encoded);records.append({'name':name,'raw_bytes':len(raw),'packed_bytes':len(encoded),'raw_sha256':hashlib.sha256(raw).hexdigest(),'offset':offset});return m[1]+f'.incbin "build/scene_lookups_packed.bin",{offset},{len(encoded)}'
 code,n=re.subn(pattern,replace,code);assert n==len(bits)>0
 source,nflags=re.subn(r'(\{[^,{}]+,scene_nearest_\d+,[^,{}]+,)(\d+)(,)',lambda m:m[1]+str(int(m[2])|128)+m[3],source);assert nflags>=n
 assets.write_text(source);assembly.write_text(code);(out/'scene_lookups_packed.bin').write_bytes(blob)
 result={'status':'pass','format':'SP32 exact 32-entry row runs and duplicate-row references','tables':len(records),'raw_bytes':sum(r['raw_bytes']for r in records),'packed_bytes':len(blob),'bytes_saved':sum(r['raw_bytes']for r in records)-len(blob),'all_original_color_index_entries_exact':True,'generator_sha256':generation,'records':records,'cached_inputs':{p:hashlib.sha256((out/p).read_bytes()).hexdigest()for p in('assets.c','high_color_blobs.s','scene_lookups_packed.bin')}};manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k not in('records','cached_inputs')},ensure_ascii=False))
if __name__=='__main__':main()
