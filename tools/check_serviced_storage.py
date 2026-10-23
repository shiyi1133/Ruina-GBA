"""Exact PackBits bytes with bounded, non-mutating audio service callbacks."""
import argparse,ctypes as C,hashlib,json,random,subprocess
from project_env import ROOT

def reference(raw):
    out=bytearray();at=0
    while at<len(raw):
        n=1
        while at+n<len(raw)and raw[at+n]==raw[at]and n<130:n+=1
        if n>=3:out.extend((128+n-3,raw[at]));at+=n;continue
        start=at;at+=1
        while at<len(raw)and at-start<128:
            if at+2<len(raw)and raw[at]==raw[at+1]==raw[at+2]:break
            at+=1
        out.append(at-start-1);out.extend(raw[start:at])
    return bytes(out)

def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default='runtime/rm2k/storage_codec.c');args=p.parse_args()
    target=ROOT/'build/storage_serviced_host.so';subprocess.run(['cc','-std=c99','-O2','-ffreestanding','-fPIC','-shared','-Iruntime/rm2k',str(ROOT/args.source),'-o',str(target)],cwd=ROOT,check=True)
    lib=C.CDLL(str(target));byte=C.POINTER(C.c_ubyte);service=C.CFUNCTYPE(None)
    for name in('pack_state_serviced','unpack_state_serviced'):getattr(lib,name).argtypes=[byte,C.c_uint,byte,C.c_uint,service]
    for name in('pack_state','unpack_state'):getattr(lib,name).argtypes=[byte,C.c_uint,byte,C.c_uint]
    rng=random.Random(0x5352414d);cases=[]
    for length in(1,2,3,127,128,129,130,131,511,512,513,39704):
        cases += [bytes([v])*length for v in(0,255)]
        cases += [bytes(rng.randrange(256)for _ in range(length))]
        cases += [(b'\0'*130+b'AB'+bytes(range(128))+b'\xff'*3)*(length//263+1)]
    calls=0
    @service
    def pump():
        nonlocal calls;calls+=1
    rows=[]
    for raw in cases:
        expected=reference(raw);source=(C.c_ubyte*len(raw)).from_buffer_copy(raw);size=len(raw)*2+32;packed=(C.c_ubyte*size)();plain=(C.c_ubyte*size)();start=calls
        n=lib.pack_state_serviced(source,len(raw),packed,size,pump);m=lib.pack_state(source,len(raw),plain,size)
        assert n==m==len(expected)and bytes(packed[:n])==expected==bytes(plain[:m])
        output=(C.c_ubyte*(len(raw)+32))(*([0xa5]*(len(raw)+32)))
        assert lib.unpack_state_serviced(packed,n,output,len(raw),pump)and bytes(output[:len(raw)])==raw and bytes(output[len(raw):])==b'\xa5'*32
        assert not lib.unpack_state_serviced(packed,n,output,len(raw)-1,pump)
        assert not lib.pack_state_serviced(source,len(raw),packed,len(expected)-1,pump)
        assert bytes(source)==raw
        rows.append({'raw_bytes':len(raw),'encoded_bytes':n,'service_calls_including_bounded_failure_cases':calls-start})
    result={'status':'pass','source':args.source,'source_sha256':hashlib.sha256((ROOT/args.source).read_bytes()).hexdigest(),'cases':len(rows),'service_calls':calls,'rows':rows,'scope':'Independent exact PackBits encoding, callback and plain API byte identity, full unpack, output guard bytes, undersized capacities and immutable source. Emulator save/cold-load and actual audio continuity tested separately.'}
    out=ROOT/'evidence/balanced_optimization_20261023/storage';out.mkdir(parents=True,exist_ok=True);(out/('host_'+result['source_sha256'][:12]+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items()if k!='rows'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
