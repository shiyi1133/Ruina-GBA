"""Direct signed-8 PCM WAV resources, retaining track IDs, pitch and pan.
Most original effects are mono. A native 8-bit DAC needs no stereo ADPCM
decoder for these; mono PCM uses the same one byte per frame ROM footprint.
Stereo original resources retain both channels. MIDI scores remain unchanged.
"""
import audioop,hashlib,io,json,struct,wave,zipfile
from pathlib import Path
import numpy as np
from project_env import ROOT,ARCHIVE
from portrait_assets import logical

def main():
 original=(ROOT/'build/audio.bin').read_bytes();manifest=json.loads((ROOT/'build/audio_manifest.json').read_text());count=struct.unpack_from('<I',original,4)[0];start=8+count*28;blobs=bytearray();indices=[];rows=[]
 with zipfile.ZipFile(ARCHIVE)as z:
  names={logical(n):n for n in z.namelist()}
  for t in manifest['tracks']:
   fields=list(struct.unpack_from('<5IhhBBH',original,8+(t['id']-1)*28));offset=(len(blobs)+3)&~3;blobs.extend(bytes(offset-len(blobs)));row=dict(t)
   if fields[1]==2:
    n=32+struct.unpack_from('<I',original,start+fields[2]+16)[0];blob=original[start+fields[2]:start+fields[2]+n]
   else:
    raw=z.read(names[t['source']]);assert hashlib.sha256(raw).hexdigest()==t['source_sha256'];w=wave.open(io.BytesIO(raw));channels=w.getnchannels();width=w.getsampwidth();pcm=w.readframes(w.getnframes());rate=w.getframerate();assert channels in(1,2)
    if width==1:pcm=audioop.bias(pcm,1,-128)
    if width!=2:pcm=audioop.lin2lin(pcm,width,2)
    if rate!=16384:pcm,_=audioop.ratecv(pcm,2,channels,rate,16384,None)
    values=np.frombuffer(pcm,np.dtype('<i2'));frames=len(values)//channels;frames&=~1;assert frames==t['frames'],(t['name'],frames,t['frames'])
    blob=(values[:frames*channels]>>8).astype(np.int8).tobytes();fields[5:9]=[0,0,0,0];fields[9]=channels;row.update(codec='signed 8-bit original WAV PCM',pcm_channels=channels,PCM_sha256=hashlib.sha256(blob).hexdigest(),loop_states=[[0,0],[0,0]])
   fields[2]=offset;indices.append(struct.pack('<5IhhBBH',*fields));blobs.extend(blob);row['stored_bytes']=len(blob);rows.append(row)
 bank=struct.pack('<2I',0x41554952,count)+b''.join(indices)+blobs
 manifest.update(tracks=rows,bytes=len(bank),direct_pcm_wav=True,format='original MIDI score bank plus direct signed-8 original WAV PCM; stable resource IDs',pcm_generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
 (ROOT/'build/audio.bin').write_bytes(bank);(ROOT/'build/audio_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2));print(json.dumps({'bytes':len(bank),'before_bytes':len(original),'WAVs':sum(t.get('pcm_channels',0)>0 for t in rows),'stereo_WAVs':sum(t.get('pcm_channels',0)==2 for t in rows),'bank_sha256':hashlib.sha256(bank).hexdigest()},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
