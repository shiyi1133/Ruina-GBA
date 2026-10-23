"""Row-addressable 4-bit PackBits for original art within the GBA ROM limit.
Each image has a 16-entry local-to-global palette. Compression changes storage,
not event data. Rows can be read without allocating a full large panorama.
"""
def encode_row(values):
 values=list(map(int,values));assert all(0<=v<16 for v in values)
 out=bytearray();at=0
 while at<len(values):
  n=1
  while at+n<len(values)and values[at+n]==values[at]and n<129:n+=1
  if n>=3:out.extend((128+n-2,values[at]));at+=n;continue
  start=at;at+=1
  while at<len(values)and at-start<128:
   if at+2<len(values)and values[at]==values[at+1]==values[at+2]:break
   at+=1
  literal=values[start:at];out.append(len(literal)-1)
  for i in range(0,len(literal),2):out.append(literal[i]<<4|(literal[i+1]if i+1<len(literal)else 0))
 return bytes(out)

def decode_row(data,width):
 out=[];at=0
 while len(out)<width:
  c=data[at];at+=1
  if c&128:n=(c&127)+2;out.extend([data[at]]*n);at+=1
  else:
   n=c+1
   for i in range(n):out.append((data[at+i//2]>>(0 if i&1 else 4))&15)
   at+=(n+1)//2
 assert len(out)==width and at==len(data)
 return bytes(out)

def encode_lz4(data):
 data=bytes(data);out=bytearray();table={};anchor=at=0
 def extension(n):
  while n>=255:out.append(255);n-=255
  out.append(n)
 while at+4<=len(data):
  key=data[at:at+4];candidates=table.get(key,[]);table[key]=(candidates+[at])[-32:]
  old=None;length=3
  # Asset conversion can spend time choosing a longer lossless match. The
  # cartridge uses exactly the same small bounded LZ4 decoder as before.
  for candidate in reversed(candidates):
   if at-candidate>65535:break
   n=4
   while at+n<len(data)and data[candidate+n]==data[at+n]:n+=1
   if n>length:old=candidate;length=n
   if at+length==len(data):break
  if old is None:at+=1;continue
  literals=at-anchor;match=length-4;out.append(min(15,literals)<<4|min(15,match))
  if literals>=15:extension(literals-15)
  out.extend(data[anchor:at]);out.extend((at-old).to_bytes(2,'little'))
  if match>=15:extension(match-15)
  end=at+length
  for i in range(at+1,end):
   if i+4<=len(data):
    key=data[i:i+4];table[key]=(table.get(key,[])+[i])[-32:]
  at=anchor=end
 literals=len(data)-anchor;out.append(min(15,literals)<<4)
 if literals>=15:extension(literals-15)
 out.extend(data[anchor:]);return bytes(out)
