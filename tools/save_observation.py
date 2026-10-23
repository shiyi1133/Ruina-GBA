"""Read-only save observations, including state before background events resume."""
import struct

def save_payload(data):
 magic,version,size,source,crc=struct.unpack_from('<5I',data)
 assert magic==0x41554952 and source==0x589a0adb
 if version!=5:return version,data[20:20+size]
 assert size<=32748 and checksum(data[20:20+size])==crc
 expected,depth=struct.unpack_from('<2I',data,20);at=28+depth*20;end=20+size;out=bytearray()
 while at<end:
  c=data[at];at+=1
  if c&128:n=(c&127)+3;out.extend(bytes([data[at]])*n);at+=1
  else:n=c+1;out.extend(data[at:at+n]);at+=n
 assert at==end and len(out)==expected
 return version,bytes(out)

def checksum(data):
 value=2166136261
 for byte in data:value=((value^byte)*16777619)&0xffffffff
 return value

def persistent_view(data):
 count=struct.unpack_from('<i',data,29764)[0];party=list(struct.unpack_from('<4i',data,29748))[:count]
 return {'map':struct.unpack_from('<i',data,29768)[0],'gold':struct.unpack_from('<i',data,29744)[0],
         'party':party,'items':data[3133:4066].hex(),
         'party_actors':{str(a):data[4068+a*196:4068+(a+1)*196].hex()for a in party},
         'progress_variables':{str(i):struct.unpack_from('<i',data,8+i*4)[0]for i in [2,26,41]}}

def check_load(e,payload):
 trace=struct.unpack('<8I',e.memory(e.symbols['save_trace'],32))
 assert trace[4]==len(payload) and trace[2]==checksum(payload),(trace,len(payload),checksum(payload))
 actual=e.memory(e.symbols['game'],len(payload));assert persistent_view(actual)==persistent_view(payload),'persistent player progress changed after resuming'
 return {'full_state_checksum_at_load_matches':True,'state_bytes_at_load':len(payload),
         'player_progress_after_background_events_resume_matches':True,
         'compared_after_resume':['map','gold','inventory','party and party actor records','origin, SP, story phase'],
         'all_bytes_after_resuming_background_events':'not required: original parallel events legitimately update scratch state'}
