"""Include instruction/data overlays when measuring ARM7 stack clearance."""
import subprocess
from drive_opening import PREFIX

def fast_memory_end(elf):
    ends=[]
    for line in subprocess.check_output([PREFIX+'nm','-S',str(elf)],text=True).splitlines():
        fields=line.split()
        if len(fields)!=4:continue
        address,size=int(fields[0],16),int(fields[1],16)
        if 0x03000000<=address<0x03008000 and size:ends.append(address+size)
    assert ends,'ELF has no sized fast-memory symbols'
    return max(ends)
