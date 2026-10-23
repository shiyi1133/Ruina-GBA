"""Compare cached immutable LCF reads with the original uncached parser."""
import ctypes as C
import hashlib,json,struct,subprocess
from project_env import ROOT

class Span(C.Structure):
 _fields_=[('data',C.c_void_p),('size',C.c_uint)]
class Reader(C.Structure):
 _fields_=[('span',Span),('pos',C.c_uint),('error',C.c_int)]
class Command(C.Structure):
 _fields_=[('code',C.c_uint),('indent',C.c_uint),('parameter_count',C.c_uint),('text',Span),('parameters',Span)]

def main():
 libs=[];source=(ROOT/'runtime/rm2k/lcf.c').read_bytes();source_digest=hashlib.sha256(source).hexdigest();snapshot=ROOT/'build/lcf_test_snapshot.c';snapshot.write_bytes(source)
 for name,extra in [('reference',[]),('cached',['-DLCF_TEST_ROM_CACHE']),('predecoded',['-DLCF_TEST_ROM_CACHE','-DRUINA_PREDECODE_COMMANDS','tests/predecoded_lcf_stub.c'])]:
  target=ROOT/'build'/('lcf_'+name+'.so')
  subprocess.run(['cc','-std=c99','-O2','-fPIC','-shared','-Iruntime/rm2k',*extra,str(snapshot),'-o',str(target)],cwd=ROOT,check=True)
  lib=C.CDLL(str(target));lib.lcf_field.argtypes=[Span,C.c_uint,C.POINTER(Span)]
  lib.lcf_next_entry.argtypes=[C.POINTER(Reader),C.POINTER(C.c_uint),C.POINTER(Span)]
  lib.lcf_number.argtypes=[C.POINTER(Reader),C.POINTER(C.c_uint)]
  lib.lcf_command_values.argtypes=[C.POINTER(Reader),C.POINTER(Command),C.POINTER(C.c_int),C.c_uint]
  lib.lcf_root.argtypes=[Span,C.POINTER(Span),C.POINTER(Span)];libs.append(lib)
 ref=libs[0];raw=(ROOT/'build/original_lcf.bin').read_bytes();buffer=(C.c_ubyte*len(raw)).in_dll(libs[-1],'original_lcf_start');base=C.addressof(buffer)
 checks={'field_reads':0,'entry_reads':0,'offset_equivalent_readers':0,'truncated_reads':0,'files':0,'command_reads':0,'command_streams':0}
 def compare_command(r,capacity=512,with_values=True):
  values=[]
  for lib in libs:
   copy=Reader(r.span,r.pos,r.error);c=Command();operands=(C.c_int*512)();C.memset(operands,0xa5,C.sizeof(operands))
   status=lib.lcf_command_values(C.byref(copy),C.byref(c),operands if with_values else None,capacity)
   values.append((status,c.code,c.indent,c.parameter_count,c.text.data,c.text.size,c.parameters.data,c.parameters.size,copy.pos,copy.error,bytes(operands)))
  assert all(v==values[0]for v in values[1:]),('command',r.span.data-base,r.span.size,r.pos,capacity,with_values,values)
  checks['command_reads']+=1;return values[0]
 def commands(s):
  if not s.data:return
  r=Reader(s,0,0);checks['command_streams']+=1
  while r.pos<s.size:
   before=r.pos;a=compare_command(r);assert a[0]
   assert compare_command(r)==a
   # Null-value boundary scans may fill the cache before a later operand read.
   compare_command(r,with_values=False);assert compare_command(r)==a
   sliced=Reader(Span(s.data+before,s.size-before),0,0);b=compare_command(sliced)
   assert b[:8]==a[:8] and b[8]==a[8]-before and b[9:]==a[9:]
   used=a[8]-before
   for size in sorted({0,1,max(0,used-1)}):
    compare_command(Reader(Span(s.data+before,size),0,0));checks['truncated_reads']+=1
   if a[3]:compare_command(r,max(0,a[3]-1))
   compare_command(Reader(s,before,1))
   r.pos=a[8]
 def field(s,key):
  values=[]
  for lib in libs:
   out=Span();status=lib.lcf_field(s,key,C.byref(out));values.append((status,out.data,out.size))
  assert all(v==values[0]for v in values[1:]),('field',s.data-base,s.size,key,values)
  checks['field_reads']+=1;return Span(values[0][1],values[0][2])
 def compare_next(r):
  values=[]
  for lib in libs:
   copy=Reader(r.span,r.pos,r.error);key=C.c_uint();out=Span()
   status=lib.lcf_next_entry(C.byref(copy),C.byref(key),C.byref(out))
   values.append((status,key.value,out.data,out.size,copy.pos,copy.error))
  assert all(v==values[0]for v in values[1:]),('entry',r.span.data-base,r.span.size,r.pos,values)
  checks['entry_reads']+=1;return values[0]
 def entries(s):
  if not s.data:return []
  r=Reader(s,0,0);n=C.c_uint();assert ref.lcf_number(C.byref(r),C.byref(n));result=[]
  for _ in range(n.value):
   before=r.pos
   a=compare_next(r);assert a[0]
   assert compare_next(r)==a
   # Same next entry and same end, but another span base: cached advancement
   # must be relative to the current reader, not the previous reader's base.
   sliced=Reader(Span(s.data+before,s.size-before),0,0);b=compare_next(sliced)
   assert b[:4]==a[:4] and b[4]==a[4]-before
   checks['offset_equivalent_readers']+=1
   for size in (0,1,max(0,s.size-before-1)):
    compare_next(Reader(Span(s.data+before,size),0,0));checks['truncated_reads']+=1
   r.pos=a[4];result.append((a[1],Span(a[2],a[3])))
  return result
 def inspect(s):
  for key in (1,2,3,4,5,8,11,12,13,21,22,23,33,34,52,999):
   a=field(s,key);b=field(s,key);assert (a.data,a.size)==(b.data,b.size)
  for size in (0,1,max(0,s.size-1)):
   field(Span(s.data,size),52);checks['truncated_reads']+=1
 for i in range(struct.unpack_from('<I',raw,8)[0]):
  descriptor=12+i*48;name=raw[descriptor:descriptor+32].split(b'\0',1)[0].decode()
  offset,size=struct.unpack_from('<II',raw,descriptor+32);head=Span();root=Span()
  assert ref.lcf_root(Span(base+offset,size),C.byref(head),C.byref(root));inspect(root);checks['files']+=1
  if name.endswith('.lmu'):
   for eid,e in entries(field(root,81)):
    inspect(e)
    for pid,p in entries(field(e,5)):inspect(p);inspect(field(p,2));commands(field(p,52))
  elif name.endswith('.ldb'):
   for table in (11,12,13,14,15,16,18,20,23,24,25):
    for key,e in entries(field(root,table)):
     inspect(e)
     if table==25:commands(field(e,22))
    # Battle troops contain another independently bounded command stream.
   for key,e in entries(field(root,15)):
    for pid,p in entries(field(e,11)):commands(field(p,12))
 counters=list((C.c_uint*8).in_dll(libs[-1],'lcf_cache_debug'));assert counters[6]>=json.loads((ROOT/'build/commands_manifest.json').read_text())['cached_commands'] and counters[4]>counters[6],counters
 report={'status':'pass','kind':'immutable original LCF data, RAM cache and predecoded ROM transport versus uncached parser, including repeated hits, alternate reader bases and truncated bounds','checks':checks,'predecoded_cache_counters':counters,'command_bank_sha256':hashlib.sha256((ROOT/'build/commands.bin').read_bytes()).hexdigest(),'source_sha256':source_digest,'source_changed_during_run':hashlib.sha256((ROOT/'runtime/rm2k/lcf.c').read_bytes()).hexdigest()!=source_digest,'original_pack_sha256':hashlib.sha256(raw).hexdigest(),'mutable_RAM':'excluded from cache in production','gameplay':'separate GBA spot checks required'}
 out=ROOT/'evidence/performance/lcf_cache.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
