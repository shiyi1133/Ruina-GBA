"""Link read-only VM views to untouched original command bytes.
No condition or operand is evaluated here. Complex/UI commands keep the
ordinary owning parser path; supported operands are explicitly padded to 8.
"""
import hashlib,json,struct
from pathlib import Path
from project_env import ROOT

def main():
 bank=(ROOT/'build/commands.bin').read_bytes();h=struct.unpack_from('<8I',bank);eligible={0,10210,10220,12010,22010,22011,12330,11410,12110,12120,12210,12220,22210,12310};rows=[]
 for i in range(h[6]):
  r=struct.unpack_from('<IHHHHIHH8I',bank,h[5]+i*52)
  if r[2]in eligible:rows.append(r)
 slots=1
 while slots<len(rows)*2:slots*=2
 index=[0]*slots
 for i,r in enumerate(rows):
  at=r[0]*2654435761&(slots-1)
  while index[at]:at=(at+1)&(slots-1)
  index[at]=i+1
 source=['#include "borrowed_commands.h"','extern const ru8 original_lcf_start[];','const BorrowedCommand borrowed_commands[]={']
 for r in rows:
  offset,advance,code,indent,tsize,toffset,psize,count,*values=r
  source.append('{{%d,%d,%d,{original_lcf_start+%d,%d},{original_lcf_start+%d,%d}},%d,%d,{%s}},'%(code,indent,count,toffset,tsize,offset+advance-psize,psize,offset,advance,','.join(str(v if v<0x80000000 else v-0x100000000)for v in values)))
 source+=['{{0,0,0,{0,0},{0,0}},4294967295U,0,{0}},','};','const unsigned short borrowed_command_index[]={'+','.join(str(v)for v in index)+'};','const ru32 borrowed_command_hash_mask=%d;'% (slots-1),''];(ROOT/'build/borrowed_commands.c').write_text('\n'.join(source));report={'format':'immutable borrowed control/variable instruction views; all live state remains in VM','commands':len(rows),'opcodes':sorted(eligible),'target_record_bytes':68,'hash_slots':slots,'target_bytes':(len(rows)+1)*68+slots*2+4,'terminal_sentinel':True,'original_pack_sha256':hashlib.sha256((ROOT/'build/original_lcf.bin').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256((ROOT/'build/borrowed_commands.c').read_bytes()).hexdigest()};(ROOT/'build/borrowed_commands_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
