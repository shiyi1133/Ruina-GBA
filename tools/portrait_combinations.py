"""Fit bounded shared OBJ palettes for up to four original face sheets.
Single-sheet pages keep their native palette. Mixed pages use a palette fitted
to exactly those sheets; the runtime remaps only newly needed portrait tiles.
"""
import hashlib,itertools,json,struct
from pathlib import Path
import numpy as np
from PIL import Image
from project_env import ROOT
from high_color_assets import rgb8,rgb555,nearest

def main():
 source=(ROOT/'build/portraits.bin').read_bytes();magic,count,records,palettes,tiles=struct.unpack_from('<5I',source);assert magic==0x43414652
 rows=[struct.unpack_from('<HHI',source,records+i*8)for i in range(count)];sheets=max(r[1]for r in rows)+1;assert sheets<=10,'Raise the profile only after checking palette-bank size against the 32 MiB ROM limit.'
 original=np.frombuffer(source,np.dtype('<u2'),sheets*256,palettes).reshape(sheets,256);pixels=[np.frombuffer(source,np.uint8,2304,tiles+r[2])for r in rows]
 samples_by_sheet=[np.concatenate([original[s][pixels[i][pixels[i]!=0]]for i,r in enumerate(rows)if r[1]==s])for s in range(sheets)]
 masks=[sum(1<<s for s in selected)for n in range(2,min(4,sheets)+1)for selected in itertools.combinations(range(sheets),n)];index=np.zeros(1<<sheets,np.uint16);fitted=[];descriptors=[];remaps=bytearray();quality=[]
 for number,mask in enumerate(masks):
  selected=[s for s in range(sheets)if mask&(1<<s)];samples=np.concatenate([samples_by_sheet[s]for s in selected]);unique=np.unique(samples)
  if len(unique)<=255:colors=unique.tolist()
  else:
   q=Image.fromarray(rgb8(samples).reshape(1,-1,3),'RGB').quantize(colors=255,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE);colors=rgb555(np.asarray(q.getpalette(),np.uint8).reshape(-1,3)[:255]).tolist()
  palette=[0]+colors;palette+=[0]*(256-len(palette));fitted.append(palette);mapped=nearest(unique,palette[1:len(colors)+1])+1;lookup=np.zeros(32768,np.uint8);lookup[unique]=mapped;record=[number*512]+[0xffffffff]*sheets
  for s in selected:
   mapping=lookup[original[s]];mapping[0]=0;record[s+1]=len(remaps);remaps.extend(mapping.tobytes())
  descriptors.append(record);index[mask]=number+1
  actual=np.asarray(palette,np.uint16)[lookup[samples]];a=rgb8(actual).astype(np.int16);b=rgb8(samples).astype(np.int16);error=np.abs(a-b)
  quality.append({'sheets_mask':mask,'source_RGB555_colors':len(unique),'changed_RGB555_pixels':int(np.count_nonzero(actual!=samples)),'visible_pixels':len(samples),'mean_RGB8_channel_error':float(error.mean()),'max_RGB8_channel_error':int(error.max())})
  if number%50==0:print('palette combinations',number+1,'/',len(masks),flush=True)
 index_at=32;records_at=index_at+len(index)*2;palette_at=records_at+len(descriptors)*(sheets+1)*4;remaps_at=palette_at+len(fitted)*512
 bank=struct.pack('<8I',0x50434d52,2,sheets,len(index),index_at,records_at,palette_at,remaps_at)+index.astype('<u2').tobytes()+np.asarray(descriptors,dtype='<u4').tobytes()+np.asarray(fitted,dtype='<u2').tobytes()+remaps
 (ROOT/'build/portrait_combinations.bin').write_bytes(bank);report={'format':'single-sheet portraits retain exact RGB555; every combination of two to four sheets has a jointly fitted 256-color palette and source-index remaps; native pixels and alpha remain intact','sheets':sheets,'portraits':count,'combinations':len(masks),'bytes':len(bank),'quality':quality,'original_bank_sha256':hashlib.sha256(source).hexdigest(),'bank_sha256':hashlib.sha256(bank).hexdigest(),'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()};(ROOT/'build/portrait_combinations_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in report.items()if k!='quality'},ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':main()
