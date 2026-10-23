"""Every linked VM view versus the original uncached parser; bounds too."""
import ctypes as C,hashlib,json,struct,subprocess
from project_env import ROOT
from check_lcf_cache import Span,Reader,Command
class Borrow(C.Structure):
 _fields_=[('command',Command),('original_offset',C.c_uint),('advance',C.c_uint),('values',C.c_int*8)]
def main():
 source=(ROOT/'runtime/rm2k/lcf.c').read_bytes();snapshot=ROOT/'build/borrow_lcf_snapshot.c';snapshot.write_bytes(source)
 flags=['cc','-std=c99','-O2','-fPIC','-shared','-ffreestanding','-Iruntime/rm2k']
 subprocess.run([*flags,str(snapshot),'-o','build/borrow_reference_host.so'],cwd=ROOT,check=True)
 subprocess.run([*flags,'-DRUINA_BORROW_COMMANDS',str(snapshot),'build/borrowed_commands.c','tests/predecoded_lcf_stub.c','-o','build/borrow_views_host.so'],cwd=ROOT,check=True)
 ref=C.CDLL(str(ROOT/'build/borrow_reference_host.so'));lib=C.CDLL(str(ROOT/'build/borrow_views_host.so'));ref.lcf_command_values.argtypes=[C.POINTER(Reader),C.POINTER(Command),C.POINTER(C.c_int),C.c_uint];lib.lcf_borrow_command.argtypes=[C.POINTER(Reader)];lib.lcf_borrow_command.restype=C.POINTER(Borrow);raw=(ROOT/'build/original_lcf.bin').read_bytes();base=C.addressof((C.c_ubyte*len(raw)).in_dll(lib,'original_lcf_start'));bank=(ROOT/'build/commands.bin').read_bytes();h=struct.unpack_from('<8I',bank);counts={'borrowed_control_instructions':0,'literal_empty_noops':0,'fallback_instructions':0,'bounded_or_error_rejections':0,'offset_equivalent_readers':0}
 def same(offset,size,shift=0):
  reader=Reader(Span(base+offset-shift,size+shift),shift,0);original=Reader(reader.span,reader.pos,reader.error);c=Command();values=(C.c_int*512)();assert ref.lcf_command_values(C.byref(original),C.byref(c),values,512);p=lib.lcf_borrow_command(C.byref(reader))
  if not p:assert reader.pos==shift and not reader.error;return False
  b=p.contents;assert reader.pos==original.pos and not reader.error;assert c.code==b.command.code
  if c.code==10:
   assert c.parameter_count==b.command.parameter_count==0 and c.text.size==b.command.text.size==0 and reader.pos-shift==4;counts['literal_empty_noops']+=1
  else:
   assert (c.code,c.indent,c.parameter_count,c.text.data,c.text.size,c.parameters.data,c.parameters.size)==(b.command.code,b.command.indent,b.command.parameter_count,b.command.text.data,b.command.text.size,b.command.parameters.data,b.command.parameters.size);assert c.parameter_count<=8;assert list(values)[:8]==list(b.values);counts['borrowed_control_instructions']+=1
  return True
 for i in range(h[6]):
  offset,advance=struct.unpack_from('<IH',bank,h[5]+i*52)
  if not same(offset,advance):counts['fallback_instructions']+=1
  assert same(offset,advance,3)==same(offset,advance);counts['offset_equivalent_readers']+=1
  for size,error in[(0,0),(1,0),(advance-1,0),(advance,1)]:
   reader=Reader(Span(base+offset,size),0,error);before=(reader.pos,reader.error);assert not lib.lcf_borrow_command(C.byref(reader));assert(reader.pos,reader.error)==before;counts['bounded_or_error_rejections']+=1
 # Mutable standalone bytes never borrow a view, even if they spell a no-op.
 ram=C.create_string_buffer(b'\x0a\x00\x00\x00');reader=Reader(Span(C.addressof(ram),4),0,0);assert not lib.lcf_borrow_command(C.byref(reader));assert reader.pos==0
 assert counts['borrowed_control_instructions']==5247*3 and counts['literal_empty_noops']>5000,counts
 report={'status':'pass','scope':'all linked immutable operand views, original parser comparison, literal no-op equivalence, shifted spans, truncated/error spans, mutable RAM excluded','checks':counts,'source_sha256':hashlib.sha256(source).hexdigest(),'linked_views_sha256':hashlib.sha256((ROOT/'build/borrowed_commands.c').read_bytes()).hexdigest(),'original_pack_sha256':hashlib.sha256(raw).hexdigest()};out=ROOT/'evidence/optimization_20261022/borrowed_commands';out.mkdir(exist_ok=True);(out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
